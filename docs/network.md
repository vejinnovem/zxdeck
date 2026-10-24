# Networking

ZX Deck is developed and tested on 32-bit Raspberry Pi OS 13 (Trixie). On
current Raspberry Pi OS releases, NetworkManager is the normal network
configuration layer, so ZX Deck wraps NetworkManager rather than editing legacy
`dhcpcd` or `wpa_supplicant` configuration directly.

## Current behaviour

The touchscreen Settings screen shows the first usable IPv4 address reported by
the operating system. Its main purpose is practical diagnostics: the owner can
read the address from the ZX Deck display and connect over SSH without first
opening the router administration page. If no non-loopback IPv4 address is
available, the UI shows `NO NETWORK`.

Settings also contains a **Wi-Fi** entry. Opening it requests a NetworkManager
scan and shows visible SSIDs, signal strength, security state and the currently
active network. `SCAN` refreshes the list. Selecting an open network connects
immediately; selecting a secured network opens the ZX Deck multi-tap keyboard
for the passphrase. NetworkManager owns and persists the resulting connection
profile, so ZX Deck does not maintain its own Wi-Fi credential database.

The on-screen keyboard includes common password punctuation in addition to
letters and digits. Wi-Fi passphrases are supplied to `nmcli --ask` through
standard input rather than being appended to the process command line, and ZX
Deck does not log them.

This implementation targets ordinary home WPA/WPA2/WPA3 personal networks.
Enterprise authentication, captive portals and unusual NetworkManager profiles
may still require external configuration. If NetworkManager refuses the service
user permission to create or activate a connection, the UI reports the failure
rather than changing system policy automatically.

## Touchscreen software updates

Software update is implemented in Settings. Entering **Software Update** fetches
`origin/main` and shows the short local and remote commit IDs. `UPDATE` is only
enabled when the checkout is on branch `main`, the working tree is clean,
`origin/main` is newer, and the update is a fast-forward.

Pressing `UPDATE` performs `git merge --ff-only origin/main`. ZX Deck never
automatically resets, stashes or overwrites local modifications. Modified,
detached, non-main or diverged checkouts are deliberately blocked and must be
handled manually.

Git runs as the ordinary ZX Deck service user. The installer adds a narrowly
scoped sudoers rule permitting only:

```text
/usr/bin/systemctl --no-block restart zxdeck.service
```

That is used after the user-approved update so the appliance loads the new
code; the updater does not receive general root access. If ZX Deck was launched
manually rather than by systemd, it asks for a manual restart instead of
starting a second instance on the TFT.

The updater tracks `main` for now. Tagged releases are preferable longer term
once the project has a release process, because stable and development channels
can then be separated.

## Planned web interface

The web frontend is optional. Settings must provide an explicit Web UI ON/OFF
control once the server exists. `OFF` means the server is actually stopped or
not started; no HTTP/WebSocket listener should remain merely because the page
is hidden. The touchscreen and tape/audio backend must continue working when
the web interface is disabled.

On phones, the future web frontend should allow a preference between the ZX
Deck custom on-screen keyboard and the operating system's native Android/iOS
keyboard for text entry. This preference does not affect the physical TFT.

## Trust boundary

Wi-Fi administration, the future Web UI and optional SMB file sharing are
designed for a trusted home/LAN environment. ZX Deck must not automatically open
router ports, expose SMB to the Internet or assume that a LAN service is safe to
make public. SMB setup is documented as an optional section in the main README.
