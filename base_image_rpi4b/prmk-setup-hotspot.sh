#!/bin/bash

INTERFACE="wlan0"
AP_SSID="MeshLinkSetup"
AP_PASS="MeshLinkSetup"

echo "Unblocking Wi-Fi..."
rfkill unblock wifi

echo "Creating and starting Wi-Fi hotspot..."
nmcli device wifi hotspot ifname "$INTERFACE" ssid "$AP_SSID" password "$AP_PASS"

if [ $? -ne 0 ]; then
    echo "Error: Failed to create Wi-Fi hotspot."
    exit 1
fi

echo "Hotspot successfully started."
