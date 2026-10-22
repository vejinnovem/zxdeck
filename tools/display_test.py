#!/usr/bin/env python3
"""Initialize the configured LCD and display eight RGB565 colour bars."""

from __future__ import annotations

import argparse
from pathlib import Path
import time

from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341


DEFAULT_CONFIG = Path(__file__).parents[1] / "config" / "hardware.zxdeck-pi-zero.toml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--hold", action="store_true")
    args = parser.parse_args()

    config = HardwareConfig.load(args.config)
    display = ILI9341(config.display)
    try:
        display.hardware_reset()
        print(f"RDID4: {display.read_register(0xD3, 4).hex(' ')}")
        print(f"RDSDR: {display.read_register(0x09, 5).hex(' ')}")
        display.initialize()
        colors = (0xFFFF, 0xFFE0, 0x07FF, 0x07E0, 0xF81F, 0xF800, 0x001F, 0x0000)
        rows = config.display.height // len(colors)
        display.set_window(0, 0, config.display.width - 1, config.display.height - 1)
        frame = bytearray()
        for color in colors:
            frame.extend(bytes((color >> 8, color & 0xFF)) * config.display.width * rows)
        display.write_rgb565(frame)
        print("Colour bars sent to the LCD.")
        if args.hold:
            print("Holding GPIO lines active; press Ctrl+C to stop.")
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

