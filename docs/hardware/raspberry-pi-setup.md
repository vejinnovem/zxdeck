# Raspberry Pi setup from a clean clone

The verified target is a 32-bit Raspberry Pi Zero W running Raspberry Pi OS 13
(trixie). The backend itself is not tied to this model.

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
sudo apt install git python3-venv python3-spidev python3-lgpio python3-pil
```

GPIO/SPI and Pillow are intentionally installed by Raspberry Pi OS rather than
vendored into the repository. Pillow is only needed by the rendered touchscreen
UI and its preview tools; the backend itself remains independent of it.

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
single CPU core available for future audio work.

## 4. Run diagnostics

```bash
PYTHONPATH=src .venv/bin/python tools/display_test.py --hold
PYTHONPATH=src .venv/bin/python tools/touch_test.py
```

Use `Ctrl+C` between tests so only one process owns the LCD reset line.

To recalibrate this physical unit without modifying tracked files:

```bash
PYTHONPATH=src .venv/bin/python tools/touch_calibrate.py
```

The default output is
`~/.local/state/zxdeck/touch-calibration.json`. Pass that file to
`tools/touch_test.py --calibration PATH` when testing the new calibration.

## 5. Generate UI previews without the LCD

The first UI milestone can be inspected as ordinary 240x320 PNG files before
it is connected to the real display:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_preview.py
```

Preview files are written to `build/ui-preview/`. The renderer is deliberately
hardware-independent. A Raspberry Pi adapter converts the completed RGB frame
to big-endian RGB565 and sends it through the existing LCD driver.

If `assets/fonts/bescii.ttf` exists, the preview tool uses it automatically.
Otherwise Pillow's fallback font is used so the layout remains testable while a
final redistributable pixel-font asset is being selected.

## 6. Run the interactive mock UI

With the tested TFT, XPT2046 and calibration in place:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_touch_demo.py
```

The demo shows the splash screen and allows touch navigation through Home,
Files, Filename and Settings. PLAY/STOP/REC, file selection and SAVE only change
mock state at this stage; the demo deliberately does not access audio, tape
parsing or storage.

Use `--no-splash` to skip the startup image. `--font PATH` can point at a chosen
pixel font during visual experiments.

## Configuration profiles

- `config/hardware.example.toml`: both display devices disabled.
- `config/hardware.zxdeck-pi-zero.toml`: tested prototype wiring and speeds.
- `config/touch-calibration.zxdeck.json`: tested calibration for this physical
  prototype and portrait orientation.

Do not commit newly generated runtime calibration files, logs, camera images,
virtual environments or Python caches.
