ee
==

A wrapper for `dd`.

Installation
------------

    $ pip install ee

Or download the source and:

    $ python setup.py install

Usage
-----

All arguments are passed directly to `dd`. `ee` spawns a `dd` process with the arguments and then monitors it with `SIGINFO` (on OS X, or `SIGUSR1` on Linux). Output reflects the amount of data copied.

If the input size can easily be determined, output will reflect the amount of data copied relative to the source size. Currently only regular files and disk device nodes that appear in `diskutil` are reported upon in this manner.

Looks something like this while running:

    $ ee if=/dev/zero of=/dev/null count=1024 bs=512m
    18.00GB/512.00GB (4%) transferred in 2.76 seconds (6.52GB/sec)

Or:

    $ ee if=/dev/zero of=/dev/null
    2.74GB transferred in 5.44 seconds (515.36MB/sec)

Todo
----

* Proper Linux support (check mounts or something rather than `diskutil`)

Disclaimer
----------

This is pretty hacky and probably buggy. If it makes your pets catch fire, then I'm sorry (not sorry).