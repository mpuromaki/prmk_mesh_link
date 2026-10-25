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

## PRMK infrastructure

PRMK infrastructure is set up to support the usage of PRMK Mesh Link devices. This infrastructure will consist of central server available via Internet (and maybe later Reticulum as well), and trusted peer devices forming backhaul mesh network. Trust is managed via cryptography and anchored in the fact that all parts of this infrastructure is owned, managed and operated by the same entity.

Backhaul network consists of multiple PRMK Mesh Link devices which have been manually enrolled by separate infrastructure mechanism. With the help of the central server peering interfaces are set up for fully dense mesh network between these trusted devices. Each link has separate IFAC codes to make sure that in case of trusted device compromise, the blast radius is kept as small as possible. Also the central server should have no mechanism to remotely control these devices; configuration is pull based and initiated by the devices. Idea is that compromise of the central server must not compromise the current network's operations. Each peer devices also have public interface for allowing connections from leaf devices. Each peer devices might also later have interfaces to the global reticulum network.

There must be a way to remote manage these devices. This likely will be SSH over internet with different random password for each device. Main way to handle updates and such should be automatic device initiated update process, with random cooldown / jitter for each device.

Some additional metrics / reporting will likely be implemented for the peer devices. This likely will include imprecise location to allow mesh map drawing at the central server. The central server will likely have some public information related to the mesh.

Two reticulum network identities are used by this infrastructure: PRMK Peering identity and PRMK public identity. Devices get these identities during the first time setup process, with peering process being locked down by some kind of time-gated manual sidechannel pre-shared key mechanism. The public identity allows leaf devices to automatically learn new peer devices interfaces via standard reticulum announce mechanisms, allowing the mesh to improve over time.

And of course users can configure additional interfaces to their devices as they see fit.
