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
sudo apt install git python3-venv python3-spidev python3-gpiozero python3-lgpio
```

GPIO/SPI packages are intentionally installed by Raspberry Pi OS rather than
vendored into the repository.

## 3. Clone and prepare Python

```bash
git clone https://github.com/vejinnovem/zxdeck.git
cd zxdeck
python3 -m venv --system-site-packages .venv
```

`--system-site-packages` exposes the distribution-provided GPIO/SPI modules to
the environment. Nothing is downloaded from PyPI. Commands below point Python
at the repository's `src/` directory explicitly. The core can be used without
GPIO/SPI packages when the display is disabled.

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

## Configuration profiles

- `config/hardware.example.toml`: both display devices disabled.
- `config/hardware.zxdeck-pi-zero.toml`: tested prototype wiring and speeds.
- `config/touch-calibration.zxdeck.json`: tested calibration for this physical
  prototype and portrait orientation.

Do not commit newly generated runtime calibration files, logs, camera images,
virtual environments or Python caches.

