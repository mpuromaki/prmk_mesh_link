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
