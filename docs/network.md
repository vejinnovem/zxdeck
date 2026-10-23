# Networking

ZX Deck is developed and tested on 32-bit Raspberry Pi OS 13 (Trixie). On
current Raspberry Pi OS releases, NetworkManager is the normal network
configuration layer, so future Wi-Fi management in ZX Deck should wrap
NetworkManager instead of editing legacy `dhcpcd` or `wpa_supplicant`
configuration directly.

## Current behaviour

The touchscreen Settings screen shows the first usable IPv4 address reported by
the operating system. Its main purpose is practical diagnostics: the owner can
read the address from the ZX Deck display and connect over SSH without first
opening the router administration page.

The address is refreshed when Settings is opened. If no non-loopback IPv4
address is available, the UI shows `NO NETWORK`.

For command-line diagnostics, Raspberry Pi OS also supports:

```bash
hostname -I
nmcli device show
```

If mDNS/Avahi is configured and the machine hostname is `zxdeck`,
`zxdeck.local` can be convenient, but the touchscreen must continue to display
an actual IPv4 address rather than relying on mDNS.

## Planned touchscreen Wi-Fi management

A future Network screen should allow the device to be moved to another trusted
Wi-Fi network without SSH. The intended flow is:

1. request a NetworkManager Wi-Fi scan;
2. show SSID, signal strength and security status with large touch targets;
3. select a network;
4. enter the passphrase with the ZX Deck on-screen keyboard;
5. connect and let NetworkManager persist the profile for future automatic
   reconnection;
6. show the resulting SSID, connection state and IPv4 address.

NetworkManager provides this functionality through `nmcli` and D-Bus. The
production implementation must not put a Wi-Fi passphrase directly in process
arguments or application logs. Prefer the NetworkManager D-Bus/secret-agent
interfaces; if a CLI adapter is retained for a limited operation, use a
protected secret mechanism supported by NetworkManager instead of embedding the
password in argv.

The UI should eventually offer at least:

- available networks and `RESCAN`;
- current SSID and signal strength;
- connect/reconnect;
- forget a stored network;
- IPv4 address;
- hostname;
- Internet/update reachability status kept separate from basic LAN connectivity.

Enterprise Wi-Fi is outside the initial target. The first implementation should
focus on normal home WPA2/WPA3 networks supported by Raspberry Pi OS.

## Planned web interface

The web frontend is optional. Settings must provide an explicit Web UI ON/OFF
control once the server exists.

`OFF` means the web server is actually stopped or not started: no HTTP or
WebSocket listener should remain open merely because the frontend is hidden.
The touchscreen and tape/audio backend must continue to work normally when the
web interface is disabled.

When enabled, the Network screen should show the usable address, for example:

```text
http://192.168.1.84:8080
```

The exact port and authentication model will be selected when the web frontend
is implemented. Do not expose the web interface to the public Internet by
default or configure router port forwarding automatically.

On phones, the future web frontend should allow a preference between the ZX
Deck custom on-screen keyboard and the operating system's native Android/iOS
keyboard for text entry. This preference does not affect the physical TFT.

## Planned software updates

The installed checkout is cloned once. Normal updates should not perform a new
`git clone`; they should operate on the existing checkout.

The intended safe flow is:

```text
check network
    -> git fetch
    -> compare local HEAD with origin/main (or a future release tag)
    -> show that an update is available
    -> user confirms UPDATE
    -> verify that the checkout is clean
    -> fast-forward only
    -> run any required installation/migration step
    -> restart zxdeck.service
```

An updater may check for availability automatically, but installation must not
happen silently. It must refuse to overwrite local modifications and should use
`git pull --ff-only` or the equivalent fetch + fast-forward operation.

Longer term, tagged releases are preferable to automatically installing every
commit from `main`.

## Trust boundary

Wi-Fi administration, the Web UI and optional SMB file sharing are designed for
a trusted home/LAN environment. ZX Deck must not automatically open router
ports, expose SMB to the Internet or assume that a LAN service is safe to make
public.

See `docs/network-file-transfer.md` for optional SMB access to the tape library.

## References

- Raspberry Pi documentation: NetworkManager is the default network
  configuration tool from Raspberry Pi OS Bookworm onwards and documents
  `nmcli dev wifi list` / `nmcli --ask dev wifi connect ...`.
- NetworkManager `nmcli` documentation describes Wi-Fi scans, connection
  profiles and protected password-file support during connection activation.
