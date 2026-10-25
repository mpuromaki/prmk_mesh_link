:warning: This repository has just been created and is nowhere near completion.

# PRMK Mesh Link

PRMK Mesh Link is a concept for an home device which acts an an gateway to the Reticulum Network. 

## Design goals

- The device will be fully owned by it's user, down to the root account password.
- But security is paramount. And so is the Zen of Reticulum.
- Common-off-the-shelf technology is used for all parts.
- Common 3D printing technologies are used for mechanical parts.
- PRMK private internet infrastructure is used to give an easy way for the user to bootstrap connectivity to the PRMK, and global, Reticulum Networks.
- Implementation is to follow zero-trust model, where this central infrastructure has minimal capabilties to control users. And compromise of any Mesh Link device must not allow compromising other such devices.
- Three tiered network model is to be used:
  - 1st is the global Reticulum Network. This is not managed in any way by PRMK or these devices. These devices are free to create interfaces to any other nodes, including global Reticulum Network connected nodes.
  - 2nd is trusted PRMK peer devices. These are Mesh Link devices that are owned by PRMK and can be easily used as trusted auto-configuring backhaul network.
  - 3rd is leaf devices. These are every other Mesh Link devices. These devices can be set up to trust PRMK infrastructure for easy and automatic connectivity. But the user can also opt to manage everything manually.
- No configuration files should be needed by end users. All configuration should be done by easy-to-use and available web interface.

## First prototype device

First device will be limited functionality prototype with computer, wifi and lora interfaces. Mechanically the device will be kept simple, even if multiple swappable interfaces are interesting option for later designs.

Prototype device will be Raspberry Pi 4b for the main computer and wifi capability and Heltec v3 for RNode lora capability. This setup is used to document how to create preconfigured image for this sbc and easy-to-use first time setup process. Plan is to have generic system image, which then is configured by the user via web interface. Updates should be automatic. Reticulum AutoInterface is used to supply Reticulum access to the whole home network via wifi.

Basic version of PRMK infrastructure is to be set up with these devices, including bootstrapping connectivity and trusted peer devices.

### Power supply

Raspberry Pi 4b supported USB-C 5V 3A power supply is used. Power is connected to the Raspberry Pi 4b, which then powers the RNode device via USB-A port as well.
