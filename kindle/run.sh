#!/bin/sh
# KindlePad — No-blink refresh daemon for Kindle Paperwhite 3
# Uses partial (GL16) refreshes by default, only doing a full (GC16) refresh
# at startup and every FULL_REFRESH_EVERY cycles to clear ghosting.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source configuration
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    . "$SCRIPT_DIR/config.sh"
else
    echo "ERROR: config.sh not found in $SCRIPT_DIR" >&2
    exit 1
fi

FBINK="/mnt/us/bin/fbink"
LOG_FILE="${KINDLEPAD_DIR}/run.log"

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

# --- Display helpers ---

display_full() {
    # Full GC16 refresh (causes blink, clears ghosting)
    $FBINK -g file="$1" -f 2>>"$LOG_FILE"
}

display_partial() {
    # Partial GL16 refresh (no blink)
    $FBINK -g file="$1" -W GL16 2>>"$LOG_FILE"
}

# --- Network ---

fetch_screen() {
    wget -q -O "$SCREEN_FILE" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/screen" 2>>"$LOG_FILE"
}

send_touch() {
    wget -q -O /dev/null \
        --post-data="{\"x\":$1,\"y\":$2}" \
        --header="Content-Type: application/json" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/touch" 2>>"$LOG_FILE"
}

# --- Touch reading ---

read_touch() {
    # Returns "x y" on stdout if touch detected, returns 1 on timeout.
    if [ -x "$SCRIPT_DIR/touch_reader.py" ] && command -v python >/dev/null 2>&1; then
        _result="$(python "$SCRIPT_DIR/touch_reader.py" "$TOUCH_DEVICE" --timeout "$REFRESH_INTERVAL" 2>>"$LOG_FILE")"
        _rc=$?
        if [ $_rc -eq 0 ] && [ -n "$_result" ]; then
            _x="$(echo "$_result" | sed 's/.*"x" *: *\([0-9]*\).*/\1/')"
            _y="$(echo "$_result" | sed 's/.*"y" *: *\([0-9]*\).*/\1/')"
            if [ -n "$_x" ] && [ -n "$_y" ]; then
                echo "${_x} ${_y}"
                return 0
            fi
        fi
        return 1
    fi

    # Fallback: sleep for the refresh interval (no touch support)
    log "WARN" "No touch reader available, sleeping ${REFRESH_INTERVAL}s"
    sleep "$REFRESH_INTERVAL"
    return 1
}

drain_stale_touches() {
    # Drain any queued touch events for 1 second so we don't replay stale taps
    if [ -x "$SCRIPT_DIR/touch_reader.py" ] && command -v python >/dev/null 2>&1; then
        python "$SCRIPT_DIR/touch_reader.py" "$TOUCH_DEVICE" --timeout 1 >/dev/null 2>&1
    fi
}

# --- Cleanup ---

cleanup() {
    log "INFO" "KindlePad shutting down"
    rm -f "$SCREEN_FILE"
    exit 0
}

# --- Main ---

main() {
    mkdir -p "$KINDLEPAD_DIR"
    log "INFO" "KindlePad run.sh starting"
    log "INFO" "Server: ${SERVER_URL}"
    log "INFO" "Refresh: ${REFRESH_INTERVAL}s, full refresh every ${FULL_REFRESH_EVERY} cycles"

    trap cleanup TERM INT

    # Stop framework and prevent screensaver
    stop_framework
    disable_screensaver

    # Clear screen and do ONE full refresh at startup
    $FBINK -c 2>>"$LOG_FILE"
    if fetch_screen; then
        display_full "$SCREEN_FILE"
        log "INFO" "Startup: full refresh done"
    else
        $FBINK -m "KindlePad: waiting for server..." -f 2>>"$LOG_FILE"
    fi

    cycle=0

    while true; do
        cycle=$((cycle + 1))

        # Wait for touch or timeout
        touch_coords=""
        if touch_coords="$(read_touch)" && [ -n "$touch_coords" ]; then
            # Touch detected — send to server, fetch updated screen
            touch_x="$(echo "$touch_coords" | cut -d' ' -f1)"
            touch_y="$(echo "$touch_coords" | cut -d' ' -f2)"

            log "INFO" "Touch: x=${touch_x}, y=${touch_y}"
            send_touch "$touch_x" "$touch_y"

            if fetch_screen; then
                # Check if this cycle needs a full refresh for ghosting
                if [ $((cycle % FULL_REFRESH_EVERY)) -eq 0 ]; then
                    display_full "$SCREEN_FILE"
                    log "INFO" "Cycle ${cycle}: full refresh (ghosting clear)"
                else
                    display_partial "$SCREEN_FILE"
                fi
            fi

            # Drain stale touch events so queued taps don't replay
            drain_stale_touches
        else
            # Timeout — fetch screen on schedule
            if fetch_screen; then
                if [ $((cycle % FULL_REFRESH_EVERY)) -eq 0 ]; then
                    display_full "$SCREEN_FILE"
                    log "INFO" "Cycle ${cycle}: full refresh (ghosting clear)"
                else
                    display_partial "$SCREEN_FILE"
                fi
            else
                log "ERROR" "Cycle ${cycle}: fetch failed"
            fi
        fi
    done
}

main "$@"
