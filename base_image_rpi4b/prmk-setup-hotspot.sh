#!/bin/bash

INTERFACE="wlan0"
AP_SSID="MeshLinkSetup"
AP_PASS="MeshLinkSetup"

echo "Unblocking Wi-Fi..."
rfkill unblock wifi
sleep 1

echo "Re-enable Wi-Fi..."
ip link set wlan0 up
sleep 1

echo "Creating and starting Wi-Fi hotspot..."
nmcli wifi radio on
sleep 1
nmcli device wifi hotspot ifname "$INTERFACE" ssid "$AP_SSID" password "$AP_PASS"

if [ $? -ne 0 ]; then
    echo "Error: Failed to create Wi-Fi hotspot."
    exit 1
fi

echo "Hotspot successfully started."
