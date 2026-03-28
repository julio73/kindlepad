#!/bin/sh
# KindlePad Kindle Configuration
# Edit these values for your setup

# Server connection
SERVER_URL="https://kindlepad.yourdomain.com"
TOKEN="your-secret-token"

# Display settings
REFRESH_INTERVAL=30        # seconds between screen refreshes
FULL_REFRESH_EVERY=10      # full e-ink refresh every N cycles (clears ghosting)

# Touch input device (PW3 typically uses event1)
TOUCH_DEVICE="/dev/input/event1"

# Paths
KINDLEPAD_DIR="/mnt/us/kindlepad"
SCREEN_FILE="/tmp/kindlepad.png"
