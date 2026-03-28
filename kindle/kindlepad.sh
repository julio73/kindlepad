#!/bin/sh
# KindlePad — Main daemon script for Kindle Paperwhite 3
# Fetches dashboard images from server, displays them, and sends touch events back.
# Designed for busybox sh on jailbroken Kindle.

# Resolve our own directory so we can source config.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Source configuration
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    . "$SCRIPT_DIR/config.sh"
else
    echo "ERROR: config.sh not found in $SCRIPT_DIR" >&2
    exit 1
fi

# --- Logging ---

LOG_FILE="${KINDLEPAD_DIR}/kindlepad.log"
MAX_LOG_SIZE=524288  # 512 KB — rotate when exceeded

log() {
    _level="$1"
    shift
    _ts="$(date '+%Y-%m-%d %H:%M:%S')"
    echo "${_ts} [${_level}] $*" >> "$LOG_FILE"
}

rotate_log() {
    if [ -f "$LOG_FILE" ]; then
        _size="$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)"
        if [ "$_size" -gt "$MAX_LOG_SIZE" ]; then
            mv "$LOG_FILE" "${LOG_FILE}.old"
            log "INFO" "Log rotated"
        fi
    fi
}

# --- Framework control ---

stop_framework() {
    log "INFO" "Stopping Kindle framework"
    stop lab126_gui >/dev/null 2>&1 || /etc/init.d/framework stop >/dev/null 2>&1
    # Wait a moment for the framework to release the framebuffer
    sleep 2
}

start_framework() {
    log "INFO" "Starting Kindle framework"
    start lab126_gui >/dev/null 2>&1 || /etc/init.d/framework start >/dev/null 2>&1
}

disable_screensaver() {
    # Prevent the Kindle screensaver from activating
    lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1
    log "INFO" "Screensaver disabled"
}

# --- Display helpers ---

display_image() {
    # $1 = image file path
    # $2 = "full" for full GC16 refresh, anything else for partial GL16
    _img="$1"
    _mode="$2"

    if [ ! -f "$_img" ]; then
        log "ERROR" "Image file not found: $_img"
        return 1
    fi

    if [ "$_mode" = "full" ]; then
        fbink -g file="$_img" -f 2>>"$LOG_FILE"
    else
        fbink -g file="$_img" -W GL16 2>>"$LOG_FILE"
    fi
}

display_error() {
    # Show error text on screen using FBInk text mode
    _msg="$1"
    fbink -m "$_msg" -f 2>>"$LOG_FILE"
    log "ERROR" "Displayed on screen: $_msg"
}

# --- Network ---

fetch_dashboard() {
    # Download the current dashboard image from the server.
    # Returns 0 on success, 1 on failure.
    wget -q -O "$SCREEN_FILE" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/screen" 2>>"$LOG_FILE"
}

send_touch() {
    # POST a touch event to the server.
    # $1 = x coordinate, $2 = y coordinate
    _x="$1"
    _y="$2"
    log "INFO" "Sending touch: x=${_x}, y=${_y}"
    wget -q -O /dev/null \
        --post-data="{\"x\":${_x},\"y\":${_y}}" \
        --header="Content-Type: application/json" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/touch" 2>>"$LOG_FILE"
}

# --- Touch reading ---

read_touch() {
    # Attempt to read a touch event within the refresh interval.
    # On success, prints "x y" to stdout and returns 0.
    # On timeout, returns 1.

    # Try Python touch reader first
    if [ -x "$SCRIPT_DIR/touch_reader.py" ] && command -v python >/dev/null 2>&1; then
        _result="$(python "$SCRIPT_DIR/touch_reader.py" "$TOUCH_DEVICE" --timeout "$REFRESH_INTERVAL" 2>>"$LOG_FILE")"
        _rc=$?
        if [ $_rc -eq 0 ] && [ -n "$_result" ]; then
            # Parse JSON: {"x":123,"y":456} — extract numbers with sed
            _x="$(echo "$_result" | sed 's/.*"x" *: *\([0-9]*\).*/\1/')"
            _y="$(echo "$_result" | sed 's/.*"y" *: *\([0-9]*\).*/\1/')"
            if [ -n "$_x" ] && [ -n "$_y" ]; then
                echo "${_x} ${_y}"
                return 0
            fi
        fi
        return 1
    fi

    # Fallback: just sleep for the refresh interval (no touch support)
    log "WARN" "No touch reader available, sleeping ${REFRESH_INTERVAL}s"
    sleep "$REFRESH_INTERVAL"
    return 1
}

# --- Cleanup ---

cleanup() {
    log "INFO" "KindlePad shutting down"
    rm -f "$SCREEN_FILE"
    start_framework
    exit 0
}

# --- Main ---

main() {
    # Ensure log directory exists
    mkdir -p "$KINDLEPAD_DIR"

    rotate_log
    log "INFO" "KindlePad starting"
    log "INFO" "Server: ${SERVER_URL}"
    log "INFO" "Refresh interval: ${REFRESH_INTERVAL}s, full refresh every ${FULL_REFRESH_EVERY} cycles"

    # Set up signal handlers
    trap cleanup TERM INT

    # Take over the Kindle
    stop_framework
    disable_screensaver

    # Show startup message
    fbink -m "KindlePad starting..." -f 2>>"$LOG_FILE"
    sleep 1

    cycle=0
    consecutive_errors=0
    MAX_CONSECUTIVE_ERRORS=10
    ERROR_BACKOFF=5

    while true; do
        cycle=$((cycle + 1))
        rotate_log

        # Determine refresh mode
        if [ $((cycle % FULL_REFRESH_EVERY)) -eq 1 ] || [ "$cycle" -eq 1 ]; then
            refresh_mode="full"
        else
            refresh_mode="partial"
        fi

        # Fetch dashboard image
        log "INFO" "Cycle ${cycle}: fetching dashboard (${refresh_mode} refresh)"
        if fetch_dashboard; then
            consecutive_errors=0

            # Display the image
            display_image "$SCREEN_FILE" "$refresh_mode"

            # Wait for touch or timeout
            touch_coords="$(read_touch)"
            if [ $? -eq 0 ] && [ -n "$touch_coords" ]; then
                # Parse "x y" from read_touch output
                touch_x="$(echo "$touch_coords" | cut -d' ' -f1)"
                touch_y="$(echo "$touch_coords" | cut -d' ' -f2)"

                # Send touch to server
                send_touch "$touch_x" "$touch_y"

                # Re-fetch and display immediately with full refresh
                log "INFO" "Re-fetching after touch"
                if fetch_dashboard; then
                    display_image "$SCREEN_FILE" "full"
                fi
            fi
        else
            consecutive_errors=$((consecutive_errors + 1))
            log "ERROR" "Failed to fetch dashboard (attempt ${consecutive_errors})"

            if [ "$consecutive_errors" -ge "$MAX_CONSECUTIVE_ERRORS" ]; then
                display_error "KindlePad: server unreachable. Retrying..."
            else
                display_error "KindlePad: fetch failed (${consecutive_errors}/${MAX_CONSECUTIVE_ERRORS})"
            fi

            # Back off on repeated errors
            _backoff=$((ERROR_BACKOFF * consecutive_errors))
            if [ "$_backoff" -gt 60 ]; then
                _backoff=60
            fi
            log "INFO" "Backing off ${_backoff}s"
            sleep "$_backoff"
        fi
    done
}

main "$@"
