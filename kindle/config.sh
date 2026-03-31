#!/bin/sh
# KindlePad Kindle Configuration
# Edit these values for your setup

# Server connection
SERVER_URL="http://YOUR_SERVER_IP:8070"
TOKEN="your-secret-token"

# Display settings
REFRESH_INTERVAL=120       # seconds between screen refreshes
FULL_REFRESH_EVERY=10      # full e-ink refresh every N cycles (clears ghosting)

# Input devices (PW3: touch=event1, power button=event0)
TOUCH_DEVICE="/dev/input/event1"
POWER_DEVICE="/dev/input/event0"

# Paths
KINDLEPAD_DIR="/mnt/us/kindlepad"
SCREEN_FILE="/tmp/kindlepad.png"
