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
    # Fast partial refresh (no blink, smoother than GL16)
    $FBINK -g file="$1" -W GL16_FAST 2>>"$LOG_FILE"
}

# --- Network ---

get_battery() {
    _cap="$(cat /sys/devices/system/wario_battery/wario_battery0/battery_capacity 2>/dev/null | tr -d '%')"
    # Clamp to 100
    if [ -n "$_cap" ] && [ "$_cap" -gt 100 ]; then
        _cap=100
    fi
    echo "$_cap"
}

is_charging() {
    _chg="$(cat /sys/devices/system/wario_charger/wario_charger0/charging 2>/dev/null)"
    [ "$_chg" = "1" ]
}

fetch_screen() {
    _batt="$(get_battery)"
    _charging=0
    if is_charging; then _charging=1; fi
    wget -q -O "$SCREEN_FILE" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/screen?battery=${_batt:-0}&charging=${_charging}" 2>>"$LOG_FILE"
}

send_touch() {
    LAST_TOUCH_ACTION=""
    _response="$(wget -q -O - \
        --post-data="{\"x\":$1,\"y\":$2}" \
        --header="Content-Type: application/json" \
        --header="Authorization: Bearer ${TOKEN}" \
        "${SERVER_URL}/touch" 2>>"$LOG_FILE")"

    # Extract action from response
    LAST_TOUCH_ACTION="$(echo "$_response" | sed -n 's/.*"action" *: *"\([^"]*\)".*/\1/p')"

    # Check if response contains brightness setting
    _brightness="$(echo "$_response" | sed -n 's/.*"brightness" *: *\([0-9]*\).*/\1/p')"
    if [ -n "$_brightness" ]; then
        echo "$_brightness" > /sys/class/backlight/max77696-bl/brightness 2>/dev/null
        log "INFO" "Brightness set to $_brightness"
    fi
}

# --- WiFi management ---

wifi_off() {
    lipc-set-prop com.lab126.wifid enable 0 >/dev/null 2>&1
    log "INFO" "WiFi disabled"
}

wifi_on() {
    lipc-set-prop com.lab126.wifid enable 1 >/dev/null 2>&1
    log "INFO" "WiFi enabled"
}

wait_for_wifi() {
    # Poll until we can reach the server (or timeout after 15s)
    _attempts=0
    while [ "$_attempts" -lt 15 ]; do
        wget -q --spider --timeout=2 "${SERVER_URL}/health" 2>/dev/null && return 0
        _attempts=$((_attempts + 1))
        sleep 1
    done
    return 1
}

# --- Brightness auto-management ---

NIGHT_START=19  # 7pm
NIGHT_END=7     # 7am
NIGHT_BRIGHTNESS=512  # low brightness for night touch
BACKLIGHT_TIMEOUT=120  # seconds before auto-dim (2 minutes)
BACKLIGHT_OFF_TIME=0  # timestamp when backlight should turn off

is_nighttime() {
    _hour="$(date +%H)"
    # Remove leading zero for comparison
    _hour="${_hour#0}"
    [ "$_hour" -ge "$NIGHT_START" ] || [ "$_hour" -lt "$NIGHT_END" ]
}

set_backlight() {
    echo "$1" > /sys/class/backlight/max77696-bl/brightness 2>/dev/null
}

handle_auto_brightness() {
    # Called on each touch. Turn on backlight briefly, auto-off after timeout.
    set_backlight "$NIGHT_BRIGHTNESS"
    BACKLIGHT_OFF_TIME=$(($(date +%s) + BACKLIGHT_TIMEOUT))
}

check_backlight_timeout() {
    # Turn off backlight if timeout has elapsed
    if [ "$BACKLIGHT_OFF_TIME" -gt 0 ]; then
        _now="$(date +%s)"
        if [ "$_now" -ge "$BACKLIGHT_OFF_TIME" ]; then
            set_backlight 0
            BACKLIGHT_OFF_TIME=0
        fi
    fi
}

# --- Touch reading ---

read_touch() {
    # Returns "x y" for touch, "power" for button press, returns 1 on timeout.
    if [ -x "$SCRIPT_DIR/touch_reader.py" ] && command -v python >/dev/null 2>&1; then
        _power_flag=""
        if [ -n "$POWER_DEVICE" ]; then
            _power_flag="--power-device $POWER_DEVICE"
        fi
        _result="$(python "$SCRIPT_DIR/touch_reader.py" "$TOUCH_DEVICE" $_power_flag --timeout "$REFRESH_INTERVAL" 2>>"$LOG_FILE")"
        _rc=$?
        if [ $_rc -eq 0 ] && [ -n "$_result" ]; then
            # Check for power button press
            if echo "$_result" | grep -q '"button"'; then
                echo "power"
                return 0
            fi
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
    # Drain ALL queued touch/button events so we don't replay stale inputs.
    # Each invocation of touch_reader.py reads one event; loop until timeout.
    if [ -x "$SCRIPT_DIR/touch_reader.py" ] && command -v python >/dev/null 2>&1; then
        _power_flag=""
        if [ -n "$POWER_DEVICE" ]; then
            _power_flag="--power-device $POWER_DEVICE"
        fi
        while python "$SCRIPT_DIR/touch_reader.py" "$TOUCH_DEVICE" $_power_flag --timeout 1 >/dev/null 2>&1; do
            : # keep draining
        done
    fi
}

# --- Sleep mode ---

enter_sleep_mode() {
    log "INFO" "Entering sleep mode"
    set_backlight 0
    BACKLIGHT_OFF_TIME=0
    wifi_off
    $FBINK -c 2>>"$LOG_FILE"  # clear screen to white

    # Wait for any touch to wake — loops on timeout until a tap arrives
    while true; do
        if read_touch >/dev/null 2>&1; then
            log "INFO" "Waking from sleep"
            drain_stale_touches
            break
        fi
    done

    # Wake: show loading state, reconnect, fetch
    handle_auto_brightness
    $FBINK -pmM "Loading..." -f 2>>"$LOG_FILE"
    wifi_on
    if wait_for_wifi; then
        if fetch_screen; then
            display_full "$SCREEN_FILE"
        fi
    else
        $FBINK -pmM "No connection — retrying..." -f 2>>"$LOG_FILE"
        log "WARN" "WiFi reconnect timed out"
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
    set_backlight 0  # start with backlight off
    if fetch_screen; then
        display_full "$SCREEN_FILE"
        log "INFO" "Startup: full refresh done"
    else
        $FBINK -m "KindlePad: waiting for server..." -f 2>>"$LOG_FILE"
    fi

    cycle=0

    while true; do
        cycle=$((cycle + 1))

        # Wait for touch, power button, or timeout
        touch_coords=""
        if touch_coords="$(read_touch)" && [ -n "$touch_coords" ]; then

            # Power button → toggle sleep
            if [ "$touch_coords" = "power" ]; then
                log "INFO" "Power button pressed"
                drain_stale_touches
                enter_sleep_mode
                cycle=0
                continue
            fi

            # Touch detected — send to server, fetch updated screen
            touch_x="$(echo "$touch_coords" | cut -d' ' -f1)"
            touch_y="$(echo "$touch_coords" | cut -d' ' -f2)"

            log "INFO" "Touch: x=${touch_x}, y=${touch_y}"
            handle_auto_brightness
            send_touch "$touch_x" "$touch_y"

            if [ "$LAST_TOUCH_ACTION" = "screen_off" ]; then
                drain_stale_touches
                enter_sleep_mode
                cycle=0
                continue
            fi

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

        # Auto-dim backlight after timeout
        check_backlight_timeout
    done
}

main "$@"
