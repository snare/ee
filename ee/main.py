from __future__ import print_function

import subprocess
import sys
import blessings
import re
import os
import stat
import plistlib
import StringIO
import platform
import time
import signal
import sys
import fcntl
import select

DEFAULT_BS = 512
BS_UNITS = {'b': 512, 'k': 1024, 'm': 1048576, 'g': 1073741824}
UNITS_OLD = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
UNITS_NEW = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
USE_NEW_DUMB_UNITS = False
SLEEP_DELAY = 0.2
START_DELAY = 0.01
TEMPL1 = "{0}/{1} ({2:0.0f}%) transferred in {3:0.2f} seconds ({4}/sec)"
TEMPL2 = "{0} transferred in {1:0.2f} seconds ({2}/sec)"
SIZE_FMT = "{0:0.2f}{1}"

PLATFORM = platform.system()

def calc_bs(args):
    # find the bs= arg
    bs_arg = None
    args = filter(lambda x: x.startswith('bs='), args)
    if len(args) > 0:        
        a = args[0].split('=')
        if len(a) > 0:
            bs_arg = a[1]

    # parse bs arg if we got one
    if bs_arg:
        # grab the unit if there is one
        unit = None
        if re.match("^[A-Za-z]$", bs_arg[-1]):
            unit = bs_arg[-1].lower()
            bs_arg = bs_arg[:-1]

        # parse any multiplications
        if 'x' in bs_arg:
            bs = 1
            for i in bs_arg.split('x'):
                 bs *= int(i)
        else:
            bs = int(bs_arg)

        # multiply by unit
        if unit in BS_UNITS:
            bs *= BS_UNITS[unit]
    else:
        bs = DEFAULT_BS

    return bs

def calc_insize(args, bs):
    insize = 0

    # see if we got a count arg
    count_arg = filter(lambda x: x.startswith('count='), args)
    if len(count_arg) and len(count_arg[0]) > 3:
        # there was a count parameter, so we know the input size
        a = count_arg[0].split('=')
        if len(a):
            count = int(a[1])
            insize = bs * count
    else:
        # no count arg, check the input arg
        if_arg = filter(lambda x: x.startswith('if='), args)
        if len(if_arg):
            infile = if_arg[0].split('=')[1]

            # check type of input file
            s = os.stat(infile)
            if stat.S_ISREG(s.st_mode):
                # regular file - get its size
                insize = s.st_size
            elif stat.S_ISCHR(s.st_mode) or stat.S_ISBLK(s.st_mode):
                # character or block device - get its size from diskutil if it knows about it
                if PLATFORM == "Darwin":
                    try:
                        plist = subprocess.check_output(["diskutil", "info", "-plist", infile])
                        d = plistlib.readPlist(StringIO.StringIO(plist))
                        insize = d['TotalSize']
                    except subprocess.CalledProcessError:
                        # diskutil returned an error - infile probably doesn't exist. whatever, dd will error.
                        pass
                elif PLATFORM == "Linux":
                    # should probably figure out a decent way to do this on linux
                    pass

    return insize

def do_dd(args, bs, insize):
    term = blessings.Terminal()
    interrupted = False

    # start the dd process
    p = subprocess.Popen(['dd'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    fcntl.fcntl(p.stderr.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    time.sleep(START_DELAY)

    # wait for it to exit
    try:
        while p.poll() is None:
            # send the signal to give us some info on stderr
            sig = signal.SIGINFO if PLATFORM == "Darwin" else signal.SIGUSR1
            p.send_signal(sig)

            # wait for output from dd
            r,w,e = select.select([p.stderr], [], [])

            try:
                # read and parse the status info
                (bytes, sec, rate) = read_status(p.stderr)

                # print status
                print(term.clear_eol + fmt_line(bytes, sec, rate, insize) + term.move_up)
            except KeyboardInterrupt:
                raise
            except:
                pass

            # sleep
            time.sleep(SLEEP_DELAY)
    except KeyboardInterrupt:
        # relay the SIGINT to dd
        p.send_signal(signal.SIGINT)
        interrupted = True

    if p.returncode == 0 or interrupted:
        # print final status
        r,w,e = select.select([p.stderr], [], [])
        (bytes, sec, rate) = read_status(p.stderr)
        print(term.clear_eol + fmt_line(bytes, sec, rate, insize))
    else:
        # print error output from dd
        sys.stderr.write(p.stderr.read())

def read_status(pipe):
    data = pipe.read()
    lines = filter(lambda x: re.match("^\d+ bytes", x), data.splitlines())
    if len(lines):
        a = lines[-1].split()
        bytes = int(a[0])
        if PLATFORM == 'Darwin':
            sec = float(a[4])
            rate = int(a[6][1:])
        else:
            sec = float(a[5])
            rate = float(a[7])*pow(1024, UNITS_OLD.index(a[8][:-2].upper()))
    else:
        raise Exception('Invalid data')

    return (bytes, sec, rate)

def fmt_b(bytes):
    base = 1024
    if USE_NEW_DUMB_UNITS:
        units = UNITS_NEW
    else:
        units = UNITS_OLD

    # find power (i suck at math)
    power = 1
    while bytes > pow(base, power):
        power += 1
    if power > 0:
        power -= 1

    # format
    fmt = SIZE_FMT.format(float(bytes)/pow(base, power), units[power])

    return fmt

def fmt_line(bytes, sec, rate, insize):
    if insize != 0:
        output = TEMPL1.format(fmt_b(bytes), fmt_b(insize), float(bytes)/insize*100, sec, fmt_b(rate))
    else:
        output = TEMPL2.format(fmt_b(bytes), sec, fmt_b(rate))
    return output

def main():
    args = sys.argv[1:]

    # determine block size
    bs = calc_bs(args)

    # determine input size
    insize = calc_insize(args, bs)

    # run dd
    do_dd(args, bs, insize)


if __name__ == "__main__":
    main()