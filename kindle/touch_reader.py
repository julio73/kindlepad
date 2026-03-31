#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KindlePad Touch Reader

Reads a single touch event from the Kindle PW3 touchscreen via evdev and
outputs JSON {"x": N, "y": N} to stdout. Designed for Python 2.7 on
Kindle, but also works with Python 3.

Usage:
    python touch_reader.py /dev/input/event1 --timeout 30
    python touch_reader.py /dev/input/event1 30

Exit codes:
    0 — touch detected, JSON printed to stdout
    1 — timeout with no touch
    2 — error (message on stderr)
"""

from __future__ import print_function

import struct
import sys
import os
import select
import json

# evdev constants
EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03
SYN_REPORT = 0x00
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
KEY_POWER = 0x74

# 32-bit ARM input_event: uint32 sec, uint32 usec, uint16 type, uint16 code, int32 value
EVENT_FORMAT = "IIHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)  # 16 bytes


def parse_args(argv):
    """Parse command-line arguments. Accepts positional or --flag style."""
    device = os.environ.get("TOUCH_DEVICE", "/dev/input/event1")
    power_device = None
    timeout = 30

    positional = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--timeout" and i + 1 < len(argv):
            try:
                timeout = int(argv[i + 1])
            except ValueError:
                print("Error: --timeout requires an integer", file=sys.stderr)
                sys.exit(2)
            i += 2
            continue
        elif arg == "--power-device" and i + 1 < len(argv):
            power_device = argv[i + 1]
            i += 2
            continue
        elif arg.startswith("--"):
            # Ignore unknown flags
            i += 1
            continue
        else:
            positional.append(arg)
        i += 1

    if len(positional) >= 1:
        device = positional[0]
    if len(positional) >= 2:
        try:
            timeout = int(positional[1])
        except ValueError:
            pass

    return device, power_device, timeout


def read_touch(device_path, power_path, timeout):
    """
    Read from touch and (optionally) power button devices until a touch
    event or power button press is received, or the timeout expires.

    Returns ("touch", x, y) for touch, ("power",) for power press,
    or None on timeout.
    """
    fds = []
    try:
        touch_fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
        fds.append(touch_fd)
    except OSError as e:
        print("Error opening %s: %s" % (device_path, e), file=sys.stderr)
        sys.exit(2)

    power_fd = None
    if power_path:
        try:
            power_fd = os.open(power_path, os.O_RDONLY | os.O_NONBLOCK)
            fds.append(power_fd)
        except OSError:
            # Power device unavailable — continue without it
            pass

    try:
        x = None
        y = None
        bufs = {fd: b"" for fd in fds}

        while True:
            readable, _, _ = select.select(fds, [], [], float(timeout))

            if not readable:
                return None

            for fd in readable:
                try:
                    chunk = os.read(fd, EVENT_SIZE * 64)
                except OSError:
                    continue

                if not chunk:
                    continue

                bufs[fd] += chunk

                while len(bufs[fd]) >= EVENT_SIZE:
                    raw = bufs[fd][:EVENT_SIZE]
                    bufs[fd] = bufs[fd][EVENT_SIZE:]

                    try:
                        _sec, _usec, ev_type, ev_code, ev_value = struct.unpack(
                            EVENT_FORMAT, raw
                        )
                    except struct.error:
                        continue

                    if fd == touch_fd:
                        if ev_type == EV_ABS:
                            if ev_code == ABS_MT_POSITION_X:
                                x = ev_value
                            elif ev_code == ABS_MT_POSITION_Y:
                                y = ev_value
                        elif ev_type == EV_SYN and ev_code == SYN_REPORT:
                            if x is not None and y is not None:
                                return ("touch", x, y)
                    elif fd == power_fd:
                        # KEY_POWER with value=1 is key-down
                        if ev_type == EV_KEY and ev_code == KEY_POWER and ev_value == 1:
                            return ("power",)
    finally:
        for fd in fds:
            os.close(fd)


def main():
    device, power_device, timeout = parse_args(sys.argv[1:])

    try:
        result = read_touch(device, power_device, timeout)
    except KeyboardInterrupt:
        sys.exit(1)

    if result is None:
        # Timeout
        sys.exit(1)

    if result[0] == "power":
        sys.stdout.write(json.dumps({"button": "power"}) + "\n")
    else:
        _, x, y = result
        sys.stdout.write(json.dumps({"x": x, "y": y}) + "\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
