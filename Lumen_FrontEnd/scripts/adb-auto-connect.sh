#!/bin/bash

# Ensure adb server is running
adb start-server > /dev/null 2>&1

echo "Scanning for Wireless Debugging services (mDNS)..."
echo "Make sure 'Wireless Debugging' is enabled on your phone and you are on the same Wi-Fi."

# Get the output of mDNS services
# We look for _adb-tls-connect._tcp which indicates a wireless debugging target
SERVICES=$(adb mdns services | grep "_adb-tls-connect._tcp")

if [ -z "$SERVICES" ]; then
  echo "No Wireless Debugging services found."
  echo "1. Go to Developer Options > Wireless Debugging."
  echo "2. Enable it."
  echo "3. Ensure your PC and Phone are on the same network."
  exit 1
fi

# Extract IP and Port
# Format is typically: <device_name> <type> <ip>:<port>
# We'll take the first one found.
TARGET=$(echo "$SERVICES" | awk '{print $3}')

if [ -z "$TARGET" ]; then
  echo "Could not parse IP and Port from service entry."
  exit 1
fi

echo "Found device at: $TARGET"
echo "Connecting..."

adb connect "$TARGET"
