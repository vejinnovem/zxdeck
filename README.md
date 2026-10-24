# zxdeck

Portable digital tape recorder/player for ZX Spectrum computers, built around a
Raspberry Pi. ZX Deck is intended to become a standalone replacement for a
physical cassette recorder: tape images are selected from the touchscreen and
played through a USB audio adapter to the Spectrum EAR input. Recording support
is planned as a core feature.

> **Transparency:** ZX Deck is a vibe-coded project. I am not a programmer;
> the project is being built with AI assistance, with changes checked by
> automated tests and real-hardware testing.
>
> **Use at your own risk:** ZX Deck is a hobby project provided as-is, without
> warranty. Software, wiring, GPIO, audio connections and hardware instructions
> should be verified before use. The author does not guarantee suitability for
> any particular hardware or configuration.

## Recommended platform

The currently recommended and verified base system is **32-bit Raspberry Pi OS
13 (Trixie)** on a **Raspberry Pi Zero W**. This is the platform used for the
real-hardware development and testing described in this repository. Other
Raspberry Pi models or OS releases may work, but they are not the primary test
target at this stage.

The current reference display is a **2.8-inch 240x320 SPI TFT** with an
ILI9341-compatible LCD controller and **XPT2046** resistive touch controller.
The TFT is optional to the architecture, but the installation instructions
below describe the complete touchscreen build.

## Current status

The tested ILI9341-compatible LCD and XPT2046 touchscreen support is working on
real hardware. The application has a 240x320 touchscreen UI with Home, Files,
Search, Filename, scrollable Settings, Output Level, Software Update, Directory
and Power screens. The Settings screen shows the current IPv4 address for SSH
and diagnostics. File-list Up/Down supports hold-to-repeat and changes to
whole-letter-group jumps during a longer hold.

PLAY decodes TAP plus the common TZX standard, turbo, pure-tone,
pulse-sequence, pure-data and direct-recording blocks in an isolated process
and streams unsigned 8-bit mono PCM to the selected ALSA playback device.
Playback calculates total generated-signal duration and reports progress back
to the Home screen. The generated tape signal has a persistent 0-100% software
output-level control; 25% is the conservative default for a new installation.

The touchscreen updater checks `origin/main`, refuses to overwrite local
changes, and only installs updates that can be applied as a Git fast-forward.
Installation happens only after the user presses `UPDATE`; it is never installed
silently. After a successful update the normal systemd installation restarts
`zxdeck.service` so the new code is loaded.

Rare generalized, CSW and control-flow TZX blocks currently fail visibly
instead of producing an incorrect signal. Recording and the web frontend are
not implemented yet.

## Technical documentation

You do **not** need to read everything in `docs/` to install and use ZX Deck.
The complete normal installation path is at the end of this README.

The documents below are reference material for development, unusual hardware,
diagnostics and troubleshooting:

- `docs/architecture.md` — application boundaries and backend/frontend design;
- `docs/ui-prototype.md` — detailed touchscreen behaviour;
- `docs/storage.md` — storage model, indexing and removable media;
- `docs/audio.md` — ALSA selection, playback progress and output level;
- `docs/network.md` — networking, Web UI plans and software-update behaviour;
- `docs/hardware/display.md` — detailed display/touch wiring and hardware notes;
- `docs/hardware/raspberry-pi-setup.md` — low-level setup, diagnostics and manual tests.

## Problems and feedback

Please use [GitHub Issues](https://github.com/vejinnovem/zxdeck/issues) for bugs,
hardware compatibility reports, installation problems and feature requests.
Issue templates are provided. For a bug, include the ZX Deck commit/version,
Raspberry Pi model, Raspberry Pi OS version, ZX Spectrum model, display/touch
hardware, USB audio device, steps to reproduce the problem and relevant logs
where possible.

# Install and run ZX Deck

This section is the normal end-user path. Follow it from top to bottom on a
fresh Raspberry Pi. Commands intended only for diagnostics or development are
not included here; if something fails, use the documents listed above.

Optional sections are marked clearly. If you do not need a feature such as SMB
file transfer, skip that section and continue.

## 1. What you need

For the reference build:

- Raspberry Pi Zero W;
- microSD card and suitable 5 V power supply;
- 32-bit Raspberry Pi OS 13 (Trixie);
- 2.8-inch 240x320 SPI TFT with XPT2046 touch if you want the local display;
- USB audio adapter with playback and capture;
- a cable from USB-audio output to the Spectrum EAR input;
- later, for recording, a connection from Spectrum MIC to USB-audio input.

The USB audio output can be much stronger than a Spectrum cassette input needs.
ZX Deck starts at 25% software output level, but that is not a calibrated
electrical safety limit for every USB adapter. Start low.

## 2. Prepare Raspberry Pi OS

Use Raspberry Pi Imager and install **32-bit Raspberry Pi OS 13 (Trixie)**.
Raspberry Pi OS Lite is sufficient if the Pi is dedicated to ZX Deck.

Before writing the card, use the Imager customization screen to set Wi-Fi, a
Linux username/password, a hostname such as `zxdeck`, and enable SSH. After the
first boot, connect for example with:

```bash
ssh YOUR_USER@zxdeck.local
```

SSH is intended for installation and troubleshooting; normal operation should
happen from the touchscreen and, later, the optional web UI.

## 3. Wire the TFT and touchscreen

The table below uses **physical Raspberry Pi header pin numbers** as the primary
reference.

| TFT / touch pin | Pi physical pin | Purpose |
|---|---:|---|
| `VCC` | 1 | 3.3 V |
| `GND` | 6 | Ground |
| `CS` | 24 | LCD CE0 / GPIO8 |
| `RESET` | 22 | LCD reset / GPIO25 |
| `DC` | 18 | LCD data-command / GPIO24 |
| `SDI (MOSI)` | 19 | SPI0 MOSI / GPIO10 |
| `SDO (MISO)` | 21 | SPI0 MISO / GPIO9 |
| `SCK` | 23 | SPI0 clock / GPIO11 |
| `LED` | 17 | 3.3 V backlight |
| `T_CLK` | 23 | shared SPI clock |
| `T_CS` | 26 | touch CE1 / GPIO7 |
| `T_DIN` | 19 | shared MOSI |
| `T_DO` | 21 | shared MISO |
| `T_IRQ` | 16 | touch IRQ / GPIO23 |

The display module's microSD slot is not part of the current reference build.

## 4. Install the required system packages

```bash
sudo apt update
sudo apt install git python3-venv python3-spidev python3-lgpio python3-pil alsa-utils
sudo raspi-config nonint do_spi 0
sudo reboot
```

Reconnect over SSH after the Pi comes back up.

## 5. Clone ZX Deck and create its Python environment

```bash
cd ~
git clone https://github.com/vejinnovem/zxdeck.git
cd zxdeck
python3 -m venv --system-site-packages .venv
mkdir -p ~/.local/share/zxdeck/tapes
```

Put `.tap`, `.tzx` or supported `.pzx` files in that directory. You can copy
files with SCP/SFTP now, use removable storage through Settings, or set up the
optional SMB share later in this README.

## 6. Calibrate the touchscreen

```bash
cd ~/zxdeck
PYTHONPATH=src .venv/bin/python tools/touch_calibrate.py
```

Touch the displayed targets. The result is saved to:

```text
~/.local/state/zxdeck/touch-calibration.json
```

ZX Deck automatically prefers this device-specific calibration over the
prototype calibration stored in the repository. Future Git updates do not
overwrite it. When calibration finishes, press `Ctrl+C` to return to the shell.

## 7. Connect the USB audio adapter

For playback:

```text
USB audio OUT  ->  ZX Spectrum EAR
```

For future recording support:

```text
ZX Spectrum MIC  ->  USB audio IN
```

After ZX Deck starts, use **Settings -> Playback** and **Settings -> Capture**
to select the USB devices. Use **Settings -> Output Level** to set the tape
signal; start with the default 25% and increase only as needed.

## 8. Install automatic startup and one-click update permission

```bash
cd ~/zxdeck
sudo .venv/bin/python tools/install_service.py
```

The installer creates and enables `zxdeck.service`, the optional early
`zxdeck-splash.service`, and `/etc/sudoers.d/zxdeck-update`. The sudoers rule is
narrow: it permits the ZX Deck user to request only a non-blocking restart of
`zxdeck.service` after an approved update. Git fetch/merge operations remain
unprivileged.

On a Raspberry Pi dedicated to ZX Deck, the following optional step applies the
boot configuration verified on the reference Pi Zero W:

```bash
sudo .venv/bin/python tools/optimize_boot.py
```

It disables completed cloud-init provisioning, unused Bluetooth and waiting for
the network before boot may continue. It also keeps compressed zram swap but
removes its SD-backed writeback file, avoiding repeated preparation of that file
during startup. NetworkManager, Wi-Fi, SSH, mDNS, GPIO, SPI and audio remain
enabled. The touchscreen may become ready before Wi-Fi reconnects.

To restore the Raspberry Pi OS defaults, run
`sudo .venv/bin/python tools/optimize_boot.py --restore` and reboot.

Reboot once:

```bash
sudo reboot
```

To install without the early splash, use `--no-boot-splash`. To omit the narrow
self-restart permission, use `--no-update-restart-sudo`; touchscreen updates can
still install code but will then require a manual restart/reboot.

## 9. First use from the touchscreen

1. Open **Settings -> Playback** and select the USB audio output.
2. Open **Settings -> Capture** and select the USB audio input if present.
3. Open **Settings -> Output Level** and keep the signal low initially.
4. Use **Tape Directory** if you want another library location.
5. Settings shows the current IPv4 address for SSH diagnostics.
6. **Software Update** checks GitHub and installs an available update only after
   you press `UPDATE`.
7. Return to **Files**, select a tape and press **PLAY**.

The playback screen shows current time, total generated tape duration and a
progress bar.

## 10. Optional: convenient file transfer over SMB

SMB is not required. Skip this section if SCP/SFTP, removable storage or another
method is enough. Use SMB only on a trusted LAN and do not expose ports 139/445
to the Internet.

```bash
sudo apt install samba
sudo smbpasswd -a "$USER"
sudo nano /etc/samba/smb.conf
```

Add this block, replacing `YOUR_USER`:

```ini
[zxdeck]
    path = /home/YOUR_USER/.local/share/zxdeck/tapes
    browseable = yes
    read only = no
    guest ok = no
    valid users = YOUR_USER
    create mask = 0664
    directory mask = 0775
```

Then:

```bash
sudo systemctl restart smbd
```

Typical paths are `\\zxdeck.local\zxdeck` on Windows and
`smb://zxdeck.local/zxdeck` on macOS/Linux. If mDNS does not resolve, use the
numeric IPv4 address displayed by ZX Deck.

## 11. Optional: allow the touchscreen Power Off button

The update restart permission does **not** grant shutdown permission. If you
want the Power Off button to shut down Linux, create a separate narrowly scoped
rule:

```bash
sudo visudo -f /etc/sudoers.d/zxdeck-poweroff
```

Replace `YOUR_USER` as appropriate:

```text
YOUR_USER ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff
```

Skip this section if you do not want ZX Deck to shut down the Pi.

## 12. Updating ZX Deck from the touchscreen

Open **Settings -> Software Update**. Entering the screen automatically runs a
fetch of `origin/main`, compares the local and remote commits, verifies that the
checkout is on `main`, checks that the working tree has no local changes, and
confirms that any update is a fast-forward.

If both commits match, the screen shows `UP TO DATE`. If a safe update exists,
it shows `UPDATE AVAILABLE` and enables `UPDATE`. Pressing it performs a
fast-forward merge, stops playback if necessary and restarts `zxdeck.service`.

The updater deliberately refuses to reset, overwrite or auto-stash local
changes and refuses diverged history. Thus a normal appliance installation gets
one-approval updating while a modified/development checkout is protected.

If ZX Deck was launched manually from a shell rather than through systemd, the
code is updated but the UI asks for a manual restart instead of starting a
second process that could contend for the TFT.

For an older installation that is receiving this updater for the first time,
run the service installer once after pulling this version:

```bash
cd ~/zxdeck
git pull --ff-only
sudo .venv/bin/python tools/install_service.py
```

After that bootstrap step, ordinary updates can be approved from the TFT.

### Manual update fallback

```bash
cd ~/zxdeck
git pull --ff-only
sudo .venv/bin/python tools/install_service.py
sudo systemctl restart zxdeck.service
```

## 13. If something does not work

The normal path above intentionally avoids diagnostic commands. For failures,
use the relevant reference document:

- display/touch/wiring: `docs/hardware/display.md`;
- detailed Raspberry Pi tests and service logs: `docs/hardware/raspberry-pi-setup.md`;
- USB audio and playback: `docs/audio.md`;
- storage/library problems: `docs/storage.md`;
- network/update behaviour: `docs/network.md`.

If the problem appears to be a ZX Deck bug or an incompatibility not covered by
the documentation, open a GitHub Issue.
