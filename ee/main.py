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

DEFAULT_BS = 512
BS_UNITS = {'b': 512, 'k': 1024, 'm': 1048576, 'g': 1073741824}
UNITS_OLD = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
UNITS_NEW = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB']
USE_NEW_DUMB_UNITS = False
SLEEP_DELAY = 0.2
START_DELAY = 0.01
TEMPL1 = "{}/{} ({:0.0f}%) transferred in {:0.2f} seconds ({}/sec)"
TEMPL2 = "{} transferred in {:0.2f} seconds ({}/sec)"
SIZE_FMT = "{:0.2f}{}"

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
                if platform.system() == "Darwin":
                    try:
                        plist = subprocess.check_output(["diskutil", "info", "-plist", infile])
                        d = plistlib.readPlist(StringIO.StringIO(plist))
                        insize = d['TotalSize']
                    except subprocess.CalledProcessError:
                        # diskutil returned an error - infile probably doesn't exist. whatever, dd will error.
                        pass
                elif platform.system() == "Linux":
                    # should probably figure out a decent way to do this on linux
                    pass

    return insize

def do_dd(args, bs, insize):
    term = blessings.Terminal()
    # print term.move_down

    # start the dd process
    p = subprocess.Popen(['dd'] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(START_DELAY)

    # wait for it to exit
    try:
        while p.poll() is None:
            # send the signal to give us some info on stderr
            sig = signal.SIGINFO if platform.system() == "Darwin" else signal.SIGUSR1
            p.send_signal(sig)

            # read and parse the status info
            (rec_in, rec_out, bytes_tx) = read_status(p.stderr)
            (bytes, sec, rate) = parse_status(bytes_tx)

            # print status
            print term.clear_eol + fmt_line(bytes, sec, rate, insize) + term.move_up

            # sleep
            time.sleep(SLEEP_DELAY)
    except KeyboardInterrupt:
        # relay the SIGINT to dd
        p.send_signal(signal.SIGINT)

    # print final status
    (rec_in, rec_out, bytes_tx) = read_status(p.stderr)
    (bytes, sec, rate) = parse_status(bytes_tx)
    print term.clear_eol + fmt_line(bytes, sec, rate, insize)

def read_status(pipe):
    rec_in = pipe.readline().strip()
    rec_out = pipe.readline().strip()
    bytes_tx = pipe.readline().strip()
    return (rec_in, rec_out, bytes_tx)

def parse_status(bytes_tx):
    a = bytes_tx.split()
    bytes = int(a[0])
    sec = float(a[4])
    rate = int(a[6][1:])
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