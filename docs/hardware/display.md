# TFT display and touchscreen wiring

This document describes the currently connected display hardware for **zxdeck**.

## Module

- PCB marking: `2.8 TFT SPI 240X320 V1.2`
- Resolution: 240x320
- Interface: SPI
- LCD controller: **likely ILI9341 or compatible**; not yet positively identified from the PCB, so software should allow the driver to be changed if needed.
- Touch controller: **XPT2046** (confirmed from the IC marking)
- Touch type: resistive
- On-board microSD slot: present, with separate `SD_CS`, `SD_MOSI`, `SD_MISO`, `SD_SCK` pads. **The SD interface is not connected yet.**

## Raspberry Pi pin numbering

The wiring below uses **physical header pin numbers** as the primary reference. BCM/GPIO numbers are included only for software configuration.

Relevant Raspberry Pi 40-pin header pins:

| Physical pin | BCM/GPIO | Function |
|---:|---:|---|
| 1 | - | 3.3 V |
| 6 | - | GND |
| 16 | GPIO23 | Touch IRQ |
| 17 | - | 3.3 V |
| 18 | GPIO24 | LCD D/C |
| 19 | GPIO10 | SPI0 MOSI |
| 21 | GPIO9 | SPI0 MISO |
| 22 | GPIO25 | LCD RESET |
| 23 | GPIO11 | SPI0 SCLK |
| 24 | GPIO8 | SPI0 CE0 / LCD CS |
| 26 | GPIO7 | SPI0 CE1 / Touch CS |

## Current LCD wiring

| TFT pin | Raspberry Pi physical pin | BCM/GPIO | Purpose |
|---|---:|---:|---|
| `VCC` | 1 | - | 3.3 V supply |
| `GND` | 6 | - | Ground |
| `CS` | 24 | GPIO8 / CE0 | LCD chip select |
| `RESET` | 22 | GPIO25 | LCD reset |
| `DC` | 18 | GPIO24 | Data/command select |
| `SDI (MOSI)` | 19 | GPIO10 / MOSI | SPI data Pi -> LCD |
| `SCK` | 23 | GPIO11 / SCLK | SPI clock |
| `LED` | 17 | - | 3.3 V backlight supply |
| `SDO (MISO)` | 21 | GPIO9 / MISO | SPI data LCD -> Pi |

## Current XPT2046 touchscreen wiring

| Touch pin | Raspberry Pi physical pin | BCM/GPIO | Purpose |
|---|---:|---:|---|
| `T_CLK` | 23 | GPIO11 / SCLK | Shared SPI clock |
| `T_CS` | 26 | GPIO7 / CE1 | Touch controller chip select |
| `T_DIN` | 19 | GPIO10 / MOSI | SPI data Pi -> XPT2046 |
| `T_DO` | 21 | GPIO9 / MISO | SPI data XPT2046 -> Pi |
| `T_IRQ` | 16 | GPIO23 | Touch interrupt |

The LCD and XPT2046 intentionally share SPI0 clock/data lines. They are selected independently with separate chip-select lines:

- LCD: physical pin 24 / CE0
- XPT2046: physical pin 26 / CE1

## SPI bus summary

```text
Raspberry Pi physical pin 19 (MOSI) -> LCD SDI + XPT2046 T_DIN
Raspberry Pi physical pin 21 (MISO) -> LCD SDO + XPT2046 T_DO
Raspberry Pi physical pin 23 (SCLK) -> LCD SCK + XPT2046 T_CLK

Raspberry Pi physical pin 24 (CE0)  -> LCD CS
Raspberry Pi physical pin 26 (CE1)  -> XPT2046 T_CS
```

## microSD interface

The display PCB exposes these separate pads:

```text
SD_CS
SD_MOSI
SD_MISO
SD_SCK
```

They are **not currently wired** in zxdeck. Do not assume the SD slot is available in software yet.

A future implementation may share `MOSI`, `MISO`, and `SCLK` with the existing SPI bus and use a separate GPIO for `SD_CS`.

## Software notes

1. Enable SPI on Raspberry Pi OS before trying to use the display.
2. Use SPI0 for the current wiring.
3. The LCD was successfully initialized with an ILI9341-compatible sequence at
   16 MHz on 2026-10-22. Register reads returned zeros, so the exact controller
   identity is still not positively confirmed, but ILI9341 compatibility is
   validated for display output.
4. The touchscreen controller is XPT2046.
5. LCD and touch may require different SPI clock speeds. Configure the SPI speed per device rather than assuming one speed is suitable for both.
6. The tested portrait orientation maps `raw_x` directly to screen X and
   `raw_y` to screen Y. Screen Y is inverted. Device-specific coefficients are
   stored in `config/touch-calibration.zxdeck.json`.
7. GPIO logic on Raspberry Pi is 3.3 V. The current wiring intentionally uses 3.3 V supply pins for the module and backlight.

## Current status

- LCD: physically connected
- XPT2046 touchscreen: physically connected
- microSD slot: not connected
- LCD output: validated with an ILI9341-compatible driver at 16 MHz
- XPT2046 input: validated at 2 MHz, including GPIO23/PENIRQ
- touchscreen calibration: validated for the current portrait orientation

## LCD smoke test

The dependency-light test in `tools/display_test.py` initializes the LCD
and displays eight RGB565 colour bars. It uses only `python3-spidev` and
`python3-gpiozero`, both available as Raspberry Pi OS packages.

Keep the process running so GPIO25 continues to hold the module's RESET line
high:

```bash
PYTHONPATH=src .venv/bin/python tools/display_test.py --hold
```

Without `--hold`, the program releases GPIO25 after sending the image. On the
tested module this resets the controller and leaves the panel white.

## Touchscreen test and calibration

`tools/touch_test.py` performs a calibrated drawing test and logs raw 12-bit
coordinates. `tools/touch_calibrate.py` presents five targets, calculates the
axis mapping, writes device-specific runtime state outside the checkout, and
then enters a calibrated drawing test.

```bash
PYTHONPATH=src .venv/bin/python tools/touch_calibrate.py
```

When an earlier calibration is available, the calibrator uses it only as a
coarse proximity check: a press more than 60 pixels from the displayed target
is rejected and the target remains active. The final fit independently checks
all five samples and requests inconsistent targets again. This behavior was
verified by deliberately pressing target 4 in the wrong location before
pressing it correctly.

The validated mapping for this panel and orientation is:

```text
screen_x =  0.06628301820669348 * raw_x - 13.655379802736576
screen_y = -0.08854512818011404 * raw_y + 351.1762393304947
```

The calibration samples covered approximately raw X `444..3519` and raw Y
`515..3774`. Values are clipped to the 240x320 screen bounds after mapping.
