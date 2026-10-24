# Raspberry Pi setup and diagnostics

> **Normal users:** the complete step-by-step installation is now in the main
> `README.md`. You do not need to work through this document to install ZX Deck.
> This page is the detailed hardware/development reference for diagnostics,
> manual tests, calibration experiments and service troubleshooting.

The verified target is a 32-bit Raspberry Pi Zero W running Raspberry Pi OS 13
(Trixie). The backend itself is not tied to this model.

## 1. Enable SPI

```bash
sudo raspi-config nonint do_spi 0
```

This writes `dtparam=spi=on` to `/boot/firmware/config.txt`. On the tested
system `/dev/spidev0.0` and `/dev/spidev0.1` appeared immediately; reboot if
they do not.

Verify:

```bash
grep '^dtparam=spi=on' /boot/firmware/config.txt
ls -l /dev/spidev0.0 /dev/spidev0.1
id
```

The service user needs access to the `spi` and `gpio` groups.

## 2. Install system packages

```bash
sudo apt update
sudo apt install git python3-venv python3-spidev python3-lgpio python3-pil alsa-utils
```

GPIO/SPI and Pillow are intentionally installed by Raspberry Pi OS rather than
vendored into the repository. `alsa-utils` supplies the `aplay`/`arecord`
commands used by playback and audio-device discovery. Pillow is only needed by
the rendered touchscreen UI and its preview tools; the backend itself remains
independent of it.

## 3. Clone and prepare Python

```bash
git clone https://github.com/vejinnovem/zxdeck.git
cd zxdeck
python3 -m venv --system-site-packages .venv
```

`--system-site-packages` exposes the distribution-provided GPIO/SPI/Pillow
modules to the environment. Nothing is downloaded from PyPI. Commands below
point Python at the repository's `src/` directory explicitly. The core can be
used without GPIO/SPI packages when the display is disabled.

The GPIO adapter polls `lgpio` directly. This avoids the background notification
threads created by a higher-level GPIO wrapper and leaves more of the Pi Zero's
single CPU core available for audio work.

## 4. Run display/touch diagnostics

These commands are for troubleshooting or hardware bring-up; they are not
required in the normal README installation path.

```bash
PYTHONPATH=src .venv/bin/python tools/display_test.py --hold
PYTHONPATH=src .venv/bin/python tools/touch_test.py
```

Use `Ctrl+C` between tests so only one process owns the LCD reset line.

To calibrate this physical unit:

```bash
PYTHONPATH=src .venv/bin/python tools/touch_calibrate.py
```

The default output is
`~/.local/state/zxdeck/touch-calibration.json`. ZX Deck automatically prefers
this device-specific file over the calibration stored in the repository. This
keeps local calibration outside the checkout and avoids Git conflicts during
updates.

## 5. Generate UI previews without the LCD

This is a development-only convenience. The UI can be rendered as ordinary
240x320 PNG files without accessing Raspberry Pi hardware:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_preview.py
```

Preview files are written to `build/ui-preview/`. The renderer is deliberately
hardware-independent. A Raspberry Pi adapter converts the completed RGB frame
to big-endian RGB565 and sends it through the existing LCD driver.

If `assets/fonts/bescii.ttf` exists, the preview tool uses it automatically.
Otherwise Pillow's fallback font is used.

## 6. Run the interactive UI manually

For development or troubleshooting, start the application directly:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_touch_demo.py
```

The application shows the production splash from
`assets/branding/zxdeck.png` and then opens the touch UI. The same branding
asset is also used by the early-boot splash.

Use `--no-splash` to skip the application startup image. `--font PATH` can
point at a chosen pixel font during visual experiments.

## Configuration profiles

- `config/hardware.example.toml`: both display devices disabled.
- `config/hardware.zxdeck-pi-zero.toml`: tested prototype wiring and speeds.
- `config/touch-calibration.zxdeck.json`: fallback calibration from the tested
  development unit. A local calibration in
  `~/.local/state/zxdeck/touch-calibration.json` takes precedence when present.

## 7. Automatic startup and early boot splash

Normal installation is covered in the README. For reference, the service
installer is:

```bash
sudo .venv/bin/python tools/install_service.py
```

It writes and enables two services:

- `/etc/systemd/system/zxdeck-splash.service` draws
  `assets/branding/zxdeck.png` as early as practical during boot and keeps the
  LCD reset line active until the normal application replaces it;
- `/etc/systemd/system/zxdeck.service` starts the normal ZX Deck application.

The splash service waits for the local filesystem and for the SPI/GPIO device
nodes, initializes the ILI9341-compatible display, draws the production image
and notifies systemd when the image is visible. It remains alive so releasing
GPIO25 cannot reset this display to white. Starting `zxdeck.service` stops the
splash holder synchronously in `ExecStartPre` and then takes ownership of
SPI/GPIO. The splash is enabled independently by `basic.target`; the main
service starts after it when present, but does not use `Wants=` (which would
try to start it during a live reinstall) or `Conflicts=` (which would let
systemd discard its start job from the boot transaction). A missing or disabled
splash is deliberately ignored by `ExecStartPre`. The splash is ordered before
`basic.target`.

This cannot eliminate the very first white interval after power-on: the TFT
backlight is powered before Linux is able to initialize and drive the display.
The purpose of the early splash is to make that interval as short as practical
without adding extra display hardware.

To install ZX Deck without the early boot splash:

```bash
sudo .venv/bin/python tools/install_service.py --no-boot-splash
```

That option also disables and removes a previously installed
`zxdeck-splash.service` unit. The production image itself remains in the
repository because the normal application uses it too.

The application runs as the unprivileged user with only the supplementary
`spi` and `gpio` groups. Its confirmed Power Off screen calls
`sudo -n systemctl poweroff`; the optional sudo policy is described in the main
README.

## Service troubleshooting

Use these only when diagnosing startup problems:

```bash
sudo systemctl status zxdeck-splash.service
sudo systemctl status zxdeck.service
sudo systemctl restart zxdeck.service
sudo journalctl -u zxdeck-splash.service -b
sudo journalctl -u zxdeck.service -f
```

After changing the branding image, a normal `git pull` is enough for both the
early splash and the application splash to use the new version on the next
start. No separate 240x320 splash asset is required; if scaling is necessary,
ZX Deck uses nearest-neighbour resizing to preserve hard pixel edges.

Do not commit newly generated runtime calibration files, logs, camera images,
virtual environments or Python caches.
