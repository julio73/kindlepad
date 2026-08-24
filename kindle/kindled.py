#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
KindlePad daemon — long-lived dashboard loop for the Kindle Paperwhite 3.

Replaces the spawn-per-tap shell loop in run.sh. A single process keeps the
evdev input devices open for its whole lifetime (so draining stale touches is
instant instead of a ~1.15s probe) and reuses one HTTP connection to the server
(so taps in quick succession skip the cold-WiFi penalty).

Behaviour preserved from run.sh: sleep/wake on the power button, WiFi off during
sleep, periodic GC16 full refresh to clear ghosting, night-time auto-brightness
with an idle timeout, and battery/charging reporting to the server.

Offline handling: when the server can't be reached, the last good screen stays
up with a server-rendered "DISCONNECTED SINCE HH:MM" banner overlaid along the
top (FBInk text would render sideways on the landscape dashboard, so the server
pre-renders rotated overlay PNGs and we cache them while connected). A tap that
never reaches the server flashes a centred OFFLINE box before restoring the
stale screen and banner.

Python 2.7 compatible (the device runs 2.7.18); also runs under Python 3.
"""

from __future__ import print_function

import json
import os
import select
import signal
import socket
import struct
import subprocess
import sys
import time

try:  # Python 2.7 (the device)
    import httplib
    import urlparse

    _http_connection = httplib.HTTPConnection
    _http_exception = httplib.HTTPException
    _urlparse = urlparse.urlparse
except ImportError:  # Python 3 (local syntax checks / dev)
    import http.client as _httplib
    import urllib.parse as _urllib_parse

    _http_connection = _httplib.HTTPConnection
    _http_exception = _httplib.HTTPException
    _urlparse = _urllib_parse.urlparse

# Shared evdev decoding lives in touch_reader.py — single source of truth.
from touch_reader import EVENT_FORMAT, EVENT_SIZE, _handle_event

BACKLIGHT_PATH = "/sys/class/backlight/max77696-bl/brightness"
BATTERY_PATH = "/sys/devices/system/wario_battery/wario_battery0/battery_capacity"
CHARGER_PATH = "/sys/devices/system/wario_charger/wario_charger0/charging"

NIGHT_BRIGHTNESS = 512  # backlight level lit on touch
BACKLIGHT_TIMEOUT = 120  # seconds before auto-dim

MAX_LOG_SIZE = 524288  # 512 KB — rotate when exceeded
READ_CHUNK = EVENT_SIZE * 64
WIFI_WAIT_ATTEMPTS = 15
OFFLINE_FLASH_SECONDS = 2  # how long the tap-failure OFFLINE box stays up


def _env_int(name, default):
    """Read an integer environment variable, falling back to ``default``."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class InputReader(object):
    """Long-lived reader over the touch and (optional) power evdev devices.

    Opens the file descriptors once and keeps them open. ``wait`` blocks for the
    next gesture; ``drain`` discards everything currently buffered without the
    per-call process spawn the old shell loop paid for.
    """

    def __init__(self, touch_device, power_device, log):
        self._log = log
        self._coords = {"x": None, "y": None}

        self.touch_fd = os.open(touch_device, os.O_RDONLY | os.O_NONBLOCK)
        self.fds = [self.touch_fd]
        self.power_fd = None
        if power_device:
            try:
                self.power_fd = os.open(power_device, os.O_RDONLY | os.O_NONBLOCK)
                self.fds.append(self.power_fd)
            except OSError:
                # Power device unavailable — continue with touch only.
                self.power_fd = None

        self._bufs = dict((fd, b"") for fd in self.fds)

    def _source(self, fd):
        if fd == self.touch_fd:
            return "touch"
        if fd == self.power_fd:
            return "power"
        return None

    def wait(self, timeout):
        """Block up to ``timeout`` seconds (``None`` = forever) for a gesture.

        Returns ``("touch", x, y)``, ``("power",)``, or ``None`` on timeout.
        """
        if timeout is not None and timeout < 0:
            timeout = 0
        deadline = None if timeout is None else time.time() + float(timeout)

        while True:
            remaining = None
            if deadline is not None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
            try:
                readable, _, _ = select.select(self.fds, [], [], remaining)
            except select.error:
                # Interrupted by a signal — the signal handler exits the process.
                continue
            if not readable:
                return None

            for fd in readable:
                result = self._read_fd(fd)
                if result is not None:
                    self._coords = {"x": None, "y": None}
                    return result

    def _read_fd(self, fd):
        """Drain ``fd``'s buffer and return the first completed gesture, if any."""
        try:
            chunk = os.read(fd, READ_CHUNK)
        except OSError:
            return None
        if not chunk:
            return None

        self._bufs[fd] += chunk
        source = self._source(fd)
        while len(self._bufs[fd]) >= EVENT_SIZE:
            raw = self._bufs[fd][:EVENT_SIZE]
            self._bufs[fd] = self._bufs[fd][EVENT_SIZE:]
            try:
                _sec, _usec, ev_type, ev_code, ev_value = struct.unpack(
                    EVENT_FORMAT, raw
                )
            except struct.error:
                continue
            result = _handle_event(source, (ev_type, ev_code, ev_value), self._coords)
            if result is not None:
                return result
        return None

    def drain(self):
        """Discard all currently-buffered events. Instant — no process spawn."""
        while True:
            try:
                readable, _, _ = select.select(self.fds, [], [], 0)
            except select.error:
                break
            if not readable:
                break
            got = False
            for fd in readable:
                try:
                    data = os.read(fd, READ_CHUNK)
                except OSError:
                    data = b""  # treat an unreadable fd as drained
                if data:
                    got = True
            if not got:
                break
        self._bufs = dict((fd, b"") for fd in self.fds)
        self._coords = {"x": None, "y": None}

    def close(self):
        for fd in self.fds:
            try:
                os.close(fd)
            except OSError as exc:
                self._log("WARN", "Closing input fd %d failed: %s" % (fd, exc))
        self.fds = []


class KeepAliveClient(object):
    """Reuses one HTTP connection to the server, reconnecting on failure.

    The persistent socket lets rapid taps skip TCP/WiFi warm-up. When the server
    closes an idle keep-alive connection, or the socket dies because WiFi was
    turned off during sleep, the next request transparently reconnects and
    retries once.
    """

    def __init__(self, base_url, token, log, timeout=10):
        parsed = _urlparse(base_url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.token = token
        self.timeout = timeout
        self._log = log
        self.conn = None

    def _connect(self):
        self.conn = _http_connection(self.host, self.port, timeout=self.timeout)

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except (socket.error, _http_exception):
                pass
            self.conn = None

    def _request(self, method, path, body=None, headers=None):
        """Issue a request, reconnecting once on a stale/closed connection.

        Returns ``(status, data)``; raises on a second consecutive failure.
        """
        last_error = None
        for attempt in (1, 2):
            try:
                if self.conn is None:
                    self._connect()
                self.conn.request(method, path, body, headers or {})
                response = self.conn.getresponse()
                data = response.read()  # must read fully to reuse the socket
                return response.status, data
            except (socket.error, _http_exception) as exc:
                last_error = exc
                self.close()
        raise last_error

    def _auth_headers(self, extra=None):
        headers = {"Authorization": "Bearer %s" % self.token}
        if extra:
            headers.update(extra)
        return headers

    def _get_to_file(self, path, dest_path, label):
        """Fetch ``path`` into ``dest_path`` atomically. Returns True on success.

        Writes to a temp file and renames into place, so a failure can never
        corrupt the previous good copy (the frozen screen is redrawn from it).
        """
        try:
            status, data = self._request("GET", path, headers=self._auth_headers())
        except (socket.error, _http_exception) as exc:
            self._log("ERROR", "%s fetch failed: %s" % (label, exc))
            return False
        if status != 200:
            self._log("ERROR", "%s fetch HTTP %s" % (label, status))
            return False
        tmp_path = dest_path + ".tmp"
        try:
            with open(tmp_path, "wb") as handle:
                handle.write(data)
            os.rename(tmp_path, dest_path)
        except (OSError, IOError) as exc:
            self._log("ERROR", "Writing %s file failed: %s" % (label, exc))
            return False
        return True

    def get_screen(self, battery, charging, dest_path):
        """Fetch the dashboard PNG into ``dest_path``. Returns True on success."""
        path = "/screen?battery=%d&charging=%d" % (battery, charging)
        return self._get_to_file(path, dest_path, "Screen")

    def get_overlay(self, name, dest_path):
        """Fetch an offline-overlay PNG into ``dest_path``. Returns True on success."""
        return self._get_to_file("/overlay/%s" % name, dest_path, "Overlay %s" % name)

    def post_touch(self, x, y):
        """POST a touch and return the parsed JSON response, or ``{}`` on error."""
        body = json.dumps({"x": x, "y": y})
        headers = self._auth_headers({"Content-Type": "application/json"})
        try:
            status, data = self._request("POST", "/touch", body, headers)
        except (socket.error, _http_exception) as exc:
            self._log("ERROR", "Touch POST failed: %s" % exc)
            return {}
        if status != 200:
            self._log("ERROR", "Touch POST HTTP %s" % status)
            return {}
        try:
            return json.loads(data.decode("utf-8"))
        except (ValueError, AttributeError):
            return {}

    def health(self):
        """Return True if the server answers /health with HTTP 200."""
        try:
            status, _ = self._request("GET", "/health")
        except (socket.error, _http_exception):
            return False
        return status == 200


class KindlePad(object):
    """The dashboard daemon: input loop, display, brightness, and sleep/wake."""

    def __init__(self):
        self.server_url = os.environ.get("SERVER_URL", "http://localhost:8070")
        self.token = os.environ.get("TOKEN", "")
        self.refresh_interval = _env_int("REFRESH_INTERVAL", 120)
        self.full_refresh_every = _env_int("FULL_REFRESH_EVERY", 10)
        self.fetch_timeout = _env_int("FETCH_TIMEOUT", 15)
        self.touch_device = os.environ.get("TOUCH_DEVICE", "/dev/input/event1")
        self.power_device = os.environ.get("POWER_DEVICE", "/dev/input/event0")
        self.kindlepad_dir = os.environ.get("KINDLEPAD_DIR", "/mnt/us/kindlepad")
        self.screen_file = os.environ.get("SCREEN_FILE", "/tmp/kindlepad.png")
        self.banner_file = os.environ.get("BANNER_FILE", "/tmp/kindlepad-banner.png")
        self.offline_file = os.environ.get(
            "OFFLINE_FILE", os.path.join(self.kindlepad_dir, "offline.png")
        )
        self.fbink = os.environ.get("FBINK", "fbink")
        self.log_file = os.environ.get(
            "LOG_FILE", os.path.join(self.kindlepad_dir, "run.log")
        )
        self.pidfile = os.environ.get("PIDFILE", "/var/run/kindlepad.pid")

        self.cycle = 0
        self.backlight_off_time = 0
        self.next_refresh_at = 0
        self.disconnected = False
        self.reader = None
        self.client = None

    def log(self, level, message):
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.log_file, "a") as handle:
                handle.write("%s [%s] %s\n" % (stamp, level, message))
        except (OSError, IOError):
            pass

    def rotate_log(self):
        try:
            size = os.path.getsize(self.log_file)
        except OSError:
            return
        if size > MAX_LOG_SIZE:
            try:
                os.rename(self.log_file, self.log_file + ".old")
            except OSError:
                return
            self.log("INFO", "Log rotated")

    def _read_sysfs(self, path):
        try:
            with open(path) as handle:
                return handle.read().strip()
        except (OSError, IOError):
            return ""

    def get_battery(self):
        raw = self._read_sysfs(BATTERY_PATH).replace("%", "")
        if not raw.isdigit():
            return 0
        return min(int(raw), 100)

    def is_charging(self):
        return self._read_sysfs(CHARGER_PATH) == "1"

    def set_backlight(self, level):
        try:
            with open(BACKLIGHT_PATH, "w") as handle:
                handle.write(str(level))
        except (OSError, IOError):
            pass

    def _fbink(self, args):
        try:
            with open(self.log_file, "a") as handle:
                subprocess.call([self.fbink] + args, stderr=handle)
        except (OSError, IOError):
            pass

    def display_full(self):
        # Full GC16 refresh (blinks, clears ghosting).
        self._fbink(["-g", "file=%s" % self.screen_file, "-f"])

    def display_partial(self):
        # Fast partial refresh (no blink).
        self._fbink(["-g", "file=%s" % self.screen_file, "-W", "GL16_FAST"])

    def clear_screen(self):
        self._fbink(["-c"])

    def show_message(self, message):
        self._fbink(["-pmM", message, "-f"])

    def refresh_display(self):
        """Redraw, choosing a full GC16 pass every Nth cycle to clear ghosting."""
        self.cycle += 1
        if self.cycle % self.full_refresh_every == 0:
            self.display_full()
            self.log("INFO", "Cycle %d: full refresh (ghosting clear)" % self.cycle)
        else:
            self.display_partial()

    def _set_wifi(self, enabled):
        try:
            subprocess.call(
                ["lipc-set-prop", "com.lab126.wifid", "enable", "1" if enabled else "0"]
            )
        except OSError as exc:
            self.log("WARN", "WiFi toggle failed: %s" % exc)

    def wifi_off(self):
        self._set_wifi(False)
        self.log("INFO", "WiFi disabled")

    def wifi_on(self):
        self._set_wifi(True)
        self.log("INFO", "WiFi enabled")

    def wait_for_wifi(self):
        """Poll the server until reachable, or give up after WIFI_WAIT_ATTEMPTS."""
        for _ in range(WIFI_WAIT_ATTEMPTS):
            if self.client.health():
                return True
            time.sleep(1)
        return False

    def handle_auto_brightness(self):
        """On each touch: light the backlight and arm the idle-off timer."""
        self.set_backlight(NIGHT_BRIGHTNESS)
        self.backlight_off_time = int(time.time()) + BACKLIGHT_TIMEOUT

    def check_backlight_timeout(self):
        if self.backlight_off_time > 0 and time.time() >= self.backlight_off_time:
            self.set_backlight(0)
            self.backlight_off_time = 0

    def fetch_screen(self):
        return self.client.get_screen(
            self.get_battery(), 1 if self.is_charging() else 0, self.screen_file
        )

    def fetch_overlays(self):
        """Cache the offline overlays after a successful screen fetch.

        The disconnected banner is stamped server-side with the current time,
        so refreshing it now bakes in the moment of the last good update —
        however long the screen then sits frozen, its "since" stays true.
        """
        if not self.client.get_overlay("disconnected", self.banner_file):
            self.log("WARN", "Failed to refresh disconnected banner")
        # The OFFLINE box is static — fetch once and keep it (it lives on
        # /mnt/us so it survives reboots).
        if not os.path.exists(self.offline_file):
            self.client.get_overlay("offline", self.offline_file)

    def mark_connected(self):
        self.disconnected = False

    def show_disconnected(self):
        """Overlay the cached banner on the frozen dashboard, once per outage.

        The banner PNG is pre-rotated like the dashboard, so the landscape top
        edge is the framebuffer's right edge — halign=EDGE pins it there, next
        to the frozen header clock it discredits.
        """
        if self.disconnected:
            return
        self.disconnected = True
        if os.path.exists(self.banner_file):
            self._fbink(
                ["-g", "file=%s,halign=EDGE" % self.banner_file, "-W", "GL16_FAST"]
            )
        else:
            # Never reached the server, so no cached banner: plain FBInk text
            # renders portrait (sideways on the landscape dashboard) but is
            # better than no indication at all.
            self._fbink(["-m", "DISCONNECTED - showing old data"])
        self.log("WARN", "Disconnected indicator shown")

    def show_offline_flash(self):
        """A tap went nowhere: flash a centred OFFLINE box, then restore the
        last good screen with the disconnected banner on top."""
        if os.path.exists(self.offline_file):
            self._fbink(
                [
                    "-g",
                    "file=%s,halign=CENTER,valign=CENTER" % self.offline_file,
                    "-W",
                    "GL16_FAST",
                ]
            )
        else:
            self._fbink(["-pmM", "OFFLINE"])
        time.sleep(OFFLINE_FLASH_SECONDS)
        if os.path.exists(self.screen_file):
            self.display_partial()
        self.disconnected = False  # force the banner over the restored screen
        self.show_disconnected()

    def _schedule_refresh(self):
        self.next_refresh_at = time.time() + self.refresh_interval

    def enter_sleep_mode(self):
        self.log("INFO", "Entering sleep mode")
        self.set_backlight(0)
        self.backlight_off_time = 0
        self.wifi_off()
        self.client.close()  # the socket dies with WiFi; reconnect on wake
        self.clear_screen()

        # Block until any touch or power press wakes us.
        while self.reader.wait(None) is None:
            pass
        self.log("INFO", "Waking from sleep")
        self.reader.drain()

        self.handle_auto_brightness()
        self.show_message("Loading...")
        self.wifi_on()
        if self.wait_for_wifi() and self.fetch_screen():
            self.display_full()
            self.mark_connected()
            self.fetch_overlays()
        else:
            self.log("WARN", "Wake: could not reach server")
            if os.path.exists(self.screen_file):
                # Show the last good screen (instead of leaving "Loading..."
                # up) with the banner; the refresh loop keeps retrying.
                self.display_full()
                self.disconnected = False
                self.show_disconnected()
            else:
                self.show_message("No connection - will keep retrying")
                self.disconnected = True

        self.cycle = 0
        self._schedule_refresh()

    def _handle_signal(self, signum, frame):
        self.log("INFO", "KindlePad shutting down")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        if self.reader is not None:
            self.reader.close()
        if self.client is not None:
            self.client.close()
        for path in (self.screen_file, self.pidfile):
            try:
                os.remove(path)
            except OSError as exc:
                if os.path.exists(path):
                    self.log("WARN", "Could not remove %s: %s" % (path, exc))

    def _apply_touch_response(self, response):
        """Apply side effects from a /touch response. Returns True to keep going,
        False if the dashboard should enter sleep (screen_off)."""
        brightness = response.get("brightness")
        if brightness is not None:
            self.set_backlight(brightness)
            self.log("INFO", "Brightness set to %s" % brightness)
        if response.get("action") == "screen_off":
            return False
        return True

    def _on_touch(self, x, y):
        self.log("INFO", "Touch: x=%d, y=%d" % (x, y))
        self.handle_auto_brightness()
        response = self.client.post_touch(x, y)
        if not response:
            # The tap never reached the server — say so, immediately.
            self.log("WARN", "Touch: server unreachable")
            self.show_offline_flash()
            self._schedule_refresh()
            self.reader.drain()
            return
        if not self._apply_touch_response(response):
            self.reader.drain()
            self.enter_sleep_mode()
            return
        if self.fetch_screen():
            self.refresh_display()
            self.mark_connected()
            self.fetch_overlays()
        else:
            # The tap was delivered but the refreshed screen wasn't — the
            # view is now stale; flag it.
            self.log("ERROR", "Post-touch fetch failed")
            self.show_disconnected()
        self._schedule_refresh()
        self.reader.drain()

    def _on_timeout(self):
        if time.time() >= self.next_refresh_at:
            if self.fetch_screen():
                self.refresh_display()
                self.mark_connected()
                self.fetch_overlays()
            else:
                self.log("ERROR", "Scheduled fetch failed")
                self.show_disconnected()
            self._schedule_refresh()

    def _loop_timeout(self):
        """Seconds to wait: bounded by the next refresh and any backlight-off."""
        now = time.time()
        timeout = max(0, self.next_refresh_at - now)
        if self.backlight_off_time > 0:
            timeout = min(timeout, max(0, self.backlight_off_time - now))
        return timeout

    def run(self):
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        if not os.path.isdir(self.kindlepad_dir):
            os.makedirs(self.kindlepad_dir)

        # Record our PID so the init script's status check works however we
        # were launched (init script, upstart, or by hand).
        try:
            with open(self.pidfile, "w") as handle:
                handle.write(str(os.getpid()))
        except (OSError, IOError):
            pass

        self.reader = InputReader(self.touch_device, self.power_device, self.log)
        self.client = KeepAliveClient(
            self.server_url, self.token, self.log, timeout=self.fetch_timeout
        )

        self.log("INFO", "KindlePad daemon starting (PID %d)" % os.getpid())
        self.log("INFO", "Server: %s" % self.server_url)
        self.log(
            "INFO",
            "Refresh: %ds, full refresh every %d cycles"
            % (self.refresh_interval, self.full_refresh_every),
        )

        # One full refresh at startup.
        self.clear_screen()
        self.set_backlight(0)
        if self.fetch_screen():
            self.display_full()
            self.log("INFO", "Startup: full refresh done")
            self.fetch_overlays()
        else:
            self.show_message("KindlePad: waiting for server...")
            self.disconnected = True  # message on screen; don't add the banner

        self._schedule_refresh()

        while True:
            self.rotate_log()
            event = self.reader.wait(self._loop_timeout())
            if event is None:
                self._on_timeout()
            elif event[0] == "power":
                self.log("INFO", "Power button pressed")
                self.reader.drain()
                self.enter_sleep_mode()
            else:
                self._on_touch(event[1], event[2])
            self.check_backlight_timeout()


def main():
    KindlePad().run()


if __name__ == "__main__":
    main()
