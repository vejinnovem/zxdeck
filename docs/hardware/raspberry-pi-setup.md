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

## 6. Run the interactive UI

With the tested TFT, XPT2046 and calibration in place:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_touch_demo.py
```

The application shows the production splash from
`assets/branding/zxdeck.png` and then opens the touch UI. The same branding
asset is also used by the optional early-boot splash described below.

Use `--no-splash` to skip the application startup image. `--font PATH` can
point at a chosen pixel font during visual experiments.

## Configuration profiles

- `config/hardware.example.toml`: both display devices disabled.
- `config/hardware.zxdeck-pi-zero.toml`: tested prototype wiring and speeds.
- `config/touch-calibration.zxdeck.json`: tested calibration for this physical
  prototype and portrait orientation.

## 7. Install automatic startup and the early boot splash

After tests pass, install the generated systemd services for the absolute path
of the current checkout:

```bash
sudo .venv/bin/python tools/install_service.py --user vejin
```

The installer writes and enables two services:

- `/etc/systemd/system/zxdeck-splash.service` draws
  `assets/branding/zxdeck.png` as early as practical during boot and exits;
- `/etc/systemd/system/zxdeck.service` starts the normal ZX Deck application.

The splash service is deliberately small. It waits for the local filesystem and
for the SPI/GPIO device nodes, initializes the ILI9341-compatible display,
draws the same production image used by the application and exits. It is
ordered before `basic.target`, so on a normal Raspberry Pi OS installation it
should replace most of the otherwise long white-screen period with the ZX Deck
branding image.

This cannot eliminate the very first white interval after power-on: the TFT
backlight is powered before Linux is able to initialize and drive the display.
The purpose of the early splash is to make that interval as short as practical
without adding extra display hardware.

To install ZX Deck without the early boot splash:

```bash
sudo .venv/bin/python tools/install_service.py --user vejin --no-boot-splash
```

That option also disables and removes a previously installed
`zxdeck-splash.service` unit. The production image itself remains in the
repository because the normal application uses it too.

The application runs as the unprivileged user with only the supplementary
`spi` and `gpio` groups. Its confirmed Power Off screen calls
`sudo -n systemctl poweroff`; configure a matching non-interactive sudo policy
before enabling that action.

Useful operations:

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
