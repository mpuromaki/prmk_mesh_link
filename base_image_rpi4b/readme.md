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
sudo apt install wget python3 python3-pip python3-cryptography python3-pyserial python3-bleak

sudo adduser --disabled-password reticulum
sudo usermod -aG dialout reticulum

sudo mkdir --parents /etc/flags
sudo mkdir --parents /opt/prmk/bin
sudo mkdir --parents /opt/prmk/system
```

### Download middleware

```sh
# Middleware required for first time setup functionality
sudo wget -O /opt/prmk/bin/prmk-setup-hotspot.sh https://raw.githubusercontent.com/mpuromaki/prmk_mesh_link/refs/heads/main/base_image_rpi4b/prmk-setup-hotspot.sh
sudo wget -O /opt/prmk/system/prmk-setup-hotspot.service https://raw.githubusercontent.com/mpuromaki/prmk_mesh_link/refs/heads/main/base_image_rpi4b/prmk-setup-hotspot.service
sudo wget -O /opt/prmk/bin/prmk-setup-server.py https://raw.githubusercontent.com/mpuromaki/prmk_mesh_link/refs/heads/main/base_image_rpi4b/prmk-setup-server.py
sudo wget -O /opt/prmk/system/prmk-setup-server.service https://raw.githubusercontent.com/mpuromaki/prmk_mesh_link/refs/heads/main/base_image_rpi4b/prmk-setup-server.service

# Middleware required for Reticulum
sudo wget -O /opt/prmk/system/prmk-rnsd.service https://raw.githubusercontent.com/mpuromaki/prmk_mesh_link/refs/heads/main/base_image_rpi4b/rnsd.service

# Set access rights
sudo chown -R root:root /opt/prmk
sudo find /opt/prmk -type d -exec chmod 755 {} +
sudo chmod 755 /opt/prmk/bin/*
sudo chmod 644 /opt/prmk/system/*
```

## Installing first time setup
```sh
sudo ln -s /opt/prmk/system/prmk-setup-hotspot.service /etc/systemd/system/
sudo ln -s /opt/prmk/system/prmk-setup-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prmk-setup-hotspot.service
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
sudo ln -s /opt/prmk/system/prmk-rnsd.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prmk-rnsd.service

exit
```

## Cleaning and creating the image

TBD.
