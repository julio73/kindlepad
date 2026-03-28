#!/bin/sh
# KindlePad Installer for Kindle Paperwhite 3
# Run this on the Kindle via SSH after copying the kindle/ directory to /mnt/us/
#
# Prerequisites:
#   - Kindle jailbroken
#   - USBNetwork installed (for SSH access)
#   - FBInk installed
#
# Usage:
#   ssh root@kindle "sh /mnt/us/kindle/install.sh"

set -e

INSTALL_DIR="/mnt/us/kindlepad"
INIT_SCRIPT="/etc/init.d/kindlepad"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Helpers ---

info() {
    echo "[INFO] $*"
}

error() {
    echo "[ERROR] $*" >&2
}

die() {
    error "$@"
    exit 1
}

# --- Pre-flight checks ---

info "KindlePad Installer"
info "==================="
echo ""

# Must be root
if [ "$(id -u)" -ne 0 ]; then
    die "This script must be run as root. Try: ssh root@kindle"
fi

# Check for FBInk
if ! command -v fbink >/dev/null 2>&1; then
    die "FBInk not found. Please install FBInk first: https://github.com/NiLuJe/FBInk"
fi
info "FBInk found: $(command -v fbink)"

# Check source files exist
for f in config.sh kindlepad.sh touch_reader.py; do
    if [ ! -f "${SOURCE_DIR}/${f}" ]; then
        die "Source file not found: ${SOURCE_DIR}/${f}"
    fi
done
info "Source files verified"

# --- Install ---

# Create install directory
info "Creating ${INSTALL_DIR}"
mkdir -p "$INSTALL_DIR"

# Copy files
info "Copying files to ${INSTALL_DIR}"
cp "${SOURCE_DIR}/config.sh"       "$INSTALL_DIR/"
cp "${SOURCE_DIR}/kindlepad.sh"    "$INSTALL_DIR/"
cp "${SOURCE_DIR}/touch_reader.py" "$INSTALL_DIR/"

# Make scripts executable
chmod +x "${INSTALL_DIR}/kindlepad.sh"
chmod +x "${INSTALL_DIR}/touch_reader.py"
chmod +x "${INSTALL_DIR}/config.sh"

info "Files installed"

# --- Create init script ---

info "Creating init script at ${INIT_SCRIPT}"
cat > "$INIT_SCRIPT" << 'INITEOF'
#!/bin/sh
# KindlePad init script
# Manages the KindlePad dashboard daemon.

KINDLEPAD_DIR="/mnt/us/kindlepad"
PIDFILE="/var/run/kindlepad.pid"
DAEMON="${KINDLEPAD_DIR}/kindlepad.sh"
LOG="${KINDLEPAD_DIR}/kindlepad.log"

case "$1" in
    start)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "KindlePad is already running (PID $(cat "$PIDFILE"))"
            exit 0
        fi

        echo "Starting KindlePad..."

        # The daemon handles stopping the framework internally
        "$DAEMON" >> "$LOG" 2>&1 &
        echo $! > "$PIDFILE"
        echo "KindlePad started (PID $(cat "$PIDFILE"))"
        ;;

    stop)
        if [ ! -f "$PIDFILE" ] || ! kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "KindlePad is not running"
            rm -f "$PIDFILE"
        else
            echo "Stopping KindlePad (PID $(cat "$PIDFILE"))..."
            kill "$(cat "$PIDFILE")"
            # Wait for clean shutdown (the daemon restarts the framework on exit)
            _count=0
            while kill -0 "$(cat "$PIDFILE")" 2>/dev/null && [ "$_count" -lt 10 ]; do
                sleep 1
                _count=$((_count + 1))
            done
            # Force kill if still alive
            if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
                kill -9 "$(cat "$PIDFILE")" 2>/dev/null
                # Restart framework manually since the daemon didn't clean up
                start lab126_gui 2>/dev/null || /etc/init.d/framework start 2>/dev/null
            fi
            rm -f "$PIDFILE"
            echo "KindlePad stopped"
        fi
        ;;

    restart)
        "$0" stop
        sleep 2
        "$0" start
        ;;

    status)
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "KindlePad is running (PID $(cat "$PIDFILE"))"
        else
            echo "KindlePad is not running"
            rm -f "$PIDFILE"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
INITEOF

chmod +x "$INIT_SCRIPT"
info "Init script created"

# --- Disable OTA updates ---

OTA_FLAG="/mnt/us/DISABLE_OTA_UPDATES"
if [ ! -f "$OTA_FLAG" ]; then
    touch "$OTA_FLAG"
    info "Kindle OTA updates disabled (created ${OTA_FLAG})"
else
    info "OTA updates already disabled"
fi

# --- Done ---

echo ""
echo "========================================="
echo "  KindlePad installation complete!"
echo "========================================="
echo ""
echo "Installed to: ${INSTALL_DIR}"
echo ""
echo "IMPORTANT: Edit the configuration before first run:"
echo "  vi ${INSTALL_DIR}/config.sh"
echo ""
echo "  - Set SERVER_URL to your KindlePad server address"
echo "  - Set TOKEN to your authentication token"
echo ""
echo "To start KindlePad:"
echo "  ${INIT_SCRIPT} start"
echo ""
echo "To stop KindlePad (restores normal Kindle operation):"
echo "  ${INIT_SCRIPT} stop"
echo ""
echo "To start on boot, add to /etc/upstart/kindlepad.conf:"
echo "  start on started filesystems"
echo "  stop on stopping filesystems"
echo "  exec ${INIT_SCRIPT} start"
echo ""
echo "To check status:"
echo "  ${INIT_SCRIPT} status"
echo ""
echo "Logs: ${INSTALL_DIR}/kindlepad.log"
echo ""
