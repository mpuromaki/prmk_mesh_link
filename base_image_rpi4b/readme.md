# Build Base Image for Raspberry Pi 4b

This document details how to build the base image for raspberry pi 4b from scratch.

## Devices

- 1x Raspberry Pi 4b, with atleast 1 GB of RAM
- Internet connectivity with an ethernet cable (so that wifi can be prepared for first time setup)

## Operating system

Latest version of 64 bit Raspberry Pi OS Lite (https://www.raspberrypi.com/software/operating-systems/).
Create user ```build``` with password ```build```. This will be deleted later.
Enable SSH with password login for build.
Flash it to 16GB or larger micro-sd card and install it to the Raspberry Pi device.

## Start

Power on the device. Connect ethernet cable. Login with user ```build```.

## Installing prerequisites

```sh
sudo apt update && sudo apt upgrade
sudo apt install python3 python3-pip python3-cryptography python3-pyserial python3-bleak

sudo adduser --disabled-password middleware

sudo adduser --disabled-password reticulum
sudo usermod -aG dialout reticulum

sudo mkdir /etc/flags
```

## Installing Reticulum

```sh
sudo su - reticulum

pip install --user --break-system-packages rns
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

exit
sudo su - reticulum

rnsd
ctrl^c

exit
```

```sh
# Clone rnsd.service to /etc/systemd/system/rnsd.service

sudo systemctl daemon-reload
sudo systemctl enable --now rnsd.service
sudo systemctl status rnsd.service # CHECK: rnsd service is running

sudo su - reticulum

rnstatus # CHECK: rnsd is available

exit
```
