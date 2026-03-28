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
EV_ABS = 0x03
SYN_REPORT = 0x00
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36

# 32-bit ARM input_event: uint32 sec, uint32 usec, uint16 type, uint16 code, int32 value
EVENT_FORMAT = "IIHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)  # 16 bytes


def parse_args(argv):
    """Parse command-line arguments. Accepts positional or --flag style."""
    device = os.environ.get("TOUCH_DEVICE", "/dev/input/event1")
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

    return device, timeout


def read_touch(device_path, timeout):
    """
    Read from the evdev device until a complete touch event is received
    or the timeout expires.

    Returns (x, y) tuple on success, None on timeout.
    """
    try:
        fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as e:
        print("Error opening %s: %s" % (device_path, e), file=sys.stderr)
        sys.exit(2)

    try:
        x = None
        y = None
        buf = b""

        while True:
            # Wait for data or timeout
            readable, _, _ = select.select([fd], [], [], float(timeout))

            if not readable:
                # Timeout
                return None

            # Read available data
            try:
                chunk = os.read(fd, EVENT_SIZE * 64)
            except OSError:
                # Device temporarily unavailable, retry
                continue

            if not chunk:
                continue

            buf += chunk

            # Process all complete events in the buffer
            while len(buf) >= EVENT_SIZE:
                raw = buf[:EVENT_SIZE]
                buf = buf[EVENT_SIZE:]

                try:
                    _sec, _usec, ev_type, ev_code, ev_value = struct.unpack(
                        EVENT_FORMAT, raw
                    )
                except struct.error:
                    # Malformed data — skip this chunk
                    continue

                if ev_type == EV_ABS:
                    if ev_code == ABS_MT_POSITION_X:
                        x = ev_value
                    elif ev_code == ABS_MT_POSITION_Y:
                        y = ev_value
                elif ev_type == EV_SYN and ev_code == SYN_REPORT:
                    # End of event packet — if we have both coordinates, we're done
                    if x is not None and y is not None:
                        return (x, y)
    finally:
        os.close(fd)


def main():
    device, timeout = parse_args(sys.argv[1:])

    try:
        result = read_touch(device, timeout)
    except KeyboardInterrupt:
        sys.exit(1)

    if result is None:
        # Timeout
        sys.exit(1)

    x, y = result
    # Output compact JSON to stdout
    sys.stdout.write(json.dumps({"x": x, "y": y}) + "\n")
    sys.stdout.flush()
    sys.exit(0)


if __name__ == "__main__":
    main()
