#!/bin/sh
# KindlePad launcher for Kindle Paperwhite 3.
#
# Prepares the device (stops the Kindle framework, disables the screensaver),
# then hands off to the long-lived Python daemon (kindled.py) which owns the
# input loop, display refreshes, and sleep/wake. Using `exec` keeps the PID
# stable so the init script's stop/kill still targets the right process.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source configuration
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    . "$SCRIPT_DIR/config.sh"
else
    echo "ERROR: config.sh not found in $SCRIPT_DIR" >&2
    exit 1
fi

FBINK="$(command -v fbink 2>/dev/null || echo /mnt/us/bin/fbink)"
LOG_FILE="${KINDLEPAD_DIR}/run.log"
PIDFILE="/var/run/kindlepad.pid"

log() {
    _ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "${_ts} [$1] $2" >> "$LOG_FILE"
}

# --- Framework control ---

stop_framework() {
    log "INFO" "Stopping Kindle framework"
    stop lab126_gui >/dev/null 2>&1
    killall awesome cvm reader >/dev/null 2>&1
    sleep 2
}

disable_screensaver() {
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1
    log "INFO" "Screensaver disabled"
}

# --- Main ---

mkdir -p "$KINDLEPAD_DIR"
log "INFO" "KindlePad launcher starting (PID $$)"

stop_framework
disable_screensaver

# Hand off to the daemon. `exec` replaces this shell so the PID recorded by the
# init script keeps pointing at the running process.
export SERVER_URL TOKEN REFRESH_INTERVAL FULL_REFRESH_EVERY
export TOUCH_DEVICE POWER_DEVICE KINDLEPAD_DIR SCREEN_FILE
export FBINK LOG_FILE PIDFILE
export FETCH_TIMEOUT BANNER_FILE OFFLINE_FILE

exec python "$SCRIPT_DIR/kindled.py"
