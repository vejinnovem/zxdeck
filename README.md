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
Search, Filename, scrollable Settings, Output Level, Directory and Power
screens. The Settings screen shows the current IPv4 address for SSH and
diagnostics. File-list Up/Down supports hold-to-repeat and changes to
whole-letter-group jumps during a longer hold.

PLAY decodes TAP plus the common TZX standard, turbo, pure-tone,
pulse-sequence, pure-data and direct-recording blocks in an isolated process
and streams unsigned 8-bit mono PCM to the selected ALSA playback device.
Playback calculates total generated-signal duration and reports progress back
to the Home screen. The generated tape signal has a persistent 0-100% software
output-level control; 25% is the conservative default for a new installation.

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
- `docs/network.md` — network architecture, future Web UI and update rules;
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

Before writing the card, use the Imager customization screen to set:

- your Wi-Fi network;
- a Linux username and password;
- hostname, for example `zxdeck`;
- SSH enabled.

After the first boot, connect over SSH. If mDNS works on your network, the host
will normally be reachable as:

```bash
ssh YOUR_USER@zxdeck.local
```

You only need SSH for installation and troubleshooting; normal operation is
intended to happen from the touchscreen and, later, the optional web UI.

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
Do not wire it as part of this setup.

## 4. Install the required system packages

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install git python3-venv python3-spidev python3-lgpio python3-pil alsa-utils
```

Enable SPI:

```bash
sudo raspi-config nonint do_spi 0
```

Reboot once after enabling SPI:

```bash
sudo reboot
```

Reconnect over SSH after the Pi comes back up.

## 5. Clone ZX Deck and create its Python environment

```bash
cd ~
git clone https://github.com/vejinnovem/zxdeck.git
cd zxdeck
python3 -m venv --system-site-packages .venv
```

ZX Deck deliberately uses the GPIO/SPI/Pillow packages supplied by Raspberry Pi
OS. No separate PyPI download is required for the current application.

Create the default tape library:

```bash
mkdir -p ~/.local/share/zxdeck/tapes
```

Put `.tap`, `.tzx` or supported `.pzx` files in this directory. You can copy
files with SCP/SFTP now, use removable storage through the Settings screen, or
set up the optional SMB share later in this README.

## 6. Calibrate the touchscreen

This is recommended once for each physical touchscreen. The repository includes
a calibration from the development unit, but resistive panels can differ.

Run:

```bash
cd ~/zxdeck
PYTHONPATH=src .venv/bin/python tools/touch_calibrate.py
```

Touch the displayed targets. The result is saved to:

```text
~/.local/state/zxdeck/touch-calibration.json
```

ZX Deck automatically prefers this device-specific calibration over the
prototype calibration stored in the repository. The file lives outside the Git
checkout, so future updates do not overwrite it.

When calibration has completed and the drawing view appears, press `Ctrl+C` to
return to the shell.

If you do not use the touchscreen, skip this step and configure the appropriate
headless/display-disabled hardware profile instead; see `docs/` for that
non-reference setup.

## 7. Connect the USB audio adapter

Connect the USB audio adapter before starting ZX Deck.

For playback:

```text
USB audio OUT  ->  ZX Spectrum EAR
```

For future recording support:

```text
ZX Spectrum MIC  ->  USB audio IN
```

You do not need to choose ALSA device names in the shell. After ZX Deck starts,
open **Settings -> Playback** and select the USB output device. Select the input
under **Settings -> Capture** when needed.

Use **Settings -> Output Level** to adjust the tape signal. Start with the
default 25% and increase only as needed for reliable loading.

## 8. Install automatic startup

From the repository directory:

```bash
cd ~/zxdeck
sudo .venv/bin/python tools/install_service.py
```

The installer creates and enables:

- `zxdeck.service` — the normal ZX Deck touchscreen application;
- `zxdeck-splash.service` — the early boot splash using
  `assets/branding/zxdeck.png`.

The normal application starts immediately. Reboot once so you can also see the
early boot splash and confirm the intended appliance-like startup flow:

```bash
sudo reboot
```

After reboot, ZX Deck should start by itself. You should no longer need SSH for
normal use.

If you deliberately do **not** want the early boot splash, install the service
with:

```bash
sudo .venv/bin/python tools/install_service.py --no-boot-splash
```

## 9. First use from the touchscreen

After ZX Deck starts:

1. Open **Settings -> Playback** and select the USB audio output.
2. Open **Settings -> Capture** and select the USB audio input if present.
3. Open **Settings -> Output Level** and keep the signal low initially.
4. Use **Tape Directory** if you want a library location other than the default.
5. The Settings screen shows the current IPv4 address for SSH diagnostics.
6. Return to **Files**, select a tape and press **PLAY**.

The playback screen shows current time, total generated tape duration and a
progress bar.

## 10. Optional: convenient file transfer over SMB

SMB is not required for ZX Deck. If you are happy using SCP/SFTP, removable
storage or another method, skip this entire section.

SMB is convenient on a trusted home network because the tape library appears as
a normal network folder on Windows, macOS or Linux. **Do not expose SMB ports
139 or 445 directly to the Internet.**

Install Samba:

```bash
sudo apt install samba
```

Create a Samba password for your existing Linux account:

```bash
sudo smbpasswd -a "$USER"
```

Edit the Samba configuration:

```bash
sudo nano /etc/samba/smb.conf
```

Add this block at the end, replacing `YOUR_USER` with your Linux username:

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

Restart Samba:

```bash
sudo systemctl restart smbd
```

Then connect from another computer using either the hostname or the IP shown in
ZX Deck Settings:

```text
Windows:  \\zxdeck.local\zxdeck
macOS:    smb://zxdeck.local/zxdeck
Linux:    smb://zxdeck.local/zxdeck
```

If `zxdeck.local` does not resolve on your network, replace it with the numeric
IPv4 address shown on the touchscreen.

## 11. Optional: allow the touchscreen Power Off button

ZX Deck deliberately runs as an unprivileged user. The Power Off screen uses a
non-interactive `systemctl poweroff`, so the Linux user needs a narrowly scoped
sudo rule if you want that button to shut the operating system down.

First check the path returned by:

```bash
command -v systemctl
```

On a normal Raspberry Pi OS installation it is `/usr/bin/systemctl`. Create:

```bash
sudo visudo -f /etc/sudoers.d/zxdeck-poweroff
```

and add one line, replacing `YOUR_USER` with your Linux username and using the
actual `systemctl` path from the previous command:

```text
YOUR_USER ALL=(root) NOPASSWD: /usr/bin/systemctl poweroff
```

Save and exit. This permission is optional; skip the whole section if you do
not want ZX Deck to be able to shut down the Pi.

## 12. Updating ZX Deck

The repository only needs to be cloned once. Later updates use Git:

```bash
cd ~/zxdeck
git pull --ff-only
sudo .venv/bin/python tools/install_service.py
sudo systemctl restart zxdeck.service
```

Re-running the service installer is intentional: most updates only need the new
code, but this also keeps systemd units synchronized if their definition
changes. The explicit restart then makes the running application load the new
code immediately.

A future touchscreen updater is planned so normal users will not need SSH for
this step.

## 13. If something does not work

The installation path above intentionally avoids diagnostic commands. When a
step fails, use the relevant reference document instead of adding diagnostic
work to every normal installation:

- display/touch/wiring: `docs/hardware/display.md`;
- detailed Raspberry Pi tests and service logs:
  `docs/hardware/raspberry-pi-setup.md`;
- USB audio and playback: `docs/audio.md`;
- storage/library problems: `docs/storage.md`;
- network design: `docs/network.md`.

If the problem appears to be a ZX Deck bug or an incompatibility not covered by
the documentation, open a GitHub Issue.
