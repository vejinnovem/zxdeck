#!/usr/bin/env python3
"""Draw calibrated XPT2046 touch positions on the configured LCD."""

from __future__ import annotations

import argparse
from pathlib import Path
import signal
import time

from zxdeck.hardware.calibration import TouchCalibration
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341
from zxdeck.hardware.xpt2046 import XPT2046


DEFAULT_CONFIG = Path(__file__).parents[1] / "config" / "hardware.zxdeck-pi-zero.toml"
BLACK, WHITE, CYAN, RED = 0x0000, 0xFFFF, 0x07FF, 0xF800


def draw_cross(display: ILI9341, x: int, y: int, color: int, radius: int = 6) -> None:
    display.fill_rect(x - radius, y - 1, radius * 2 + 1, 3, color)
    display.fill_rect(x - 1, y - radius, 3, radius * 2 + 1, color)


def draw_screen(display: ILI9341) -> None:
    width, height = display.config.width, display.config.height
    display.fill(BLACK)
    display.fill_rect(0, 0, width, 2, WHITE)
    display.fill_rect(0, height - 2, width, 2, WHITE)
    display.fill_rect(0, 0, 2, height, WHITE)
    display.fill_rect(width - 2, 0, 2, height, WHITE)
    draw_cross(display, width // 2, height // 2, RED, 8)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--calibration", type=Path)
    args = parser.parse_args()
    config = HardwareConfig.load(args.config)
    calibration_path = args.calibration or config.touch.calibration_file
    if calibration_path is None:
        parser.error("a calibration file is required")
    calibration = TouchCalibration.load(calibration_path)

    display = ILI9341(config.display)
    touch = XPT2046(config.touch)
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        display.initialize()
        draw_screen(display)
        print("Calibrated touch drawing test ready.", flush=True)
        last_draw = 0.0
        while running:
            if not touch.pressed:
                time.sleep(0.01)
                continue
            raw_x, raw_y = touch.read_raw()
            now = time.monotonic()
            if now - last_draw >= 0.03:
                x, y = calibration.map(
                    raw_x, raw_y, config.display.width, config.display.height
                )
                print(f"raw_x={raw_x:4d} raw_y={raw_y:4d} -> x={x:3d} y={y:3d}", flush=True)
                draw_cross(display, x, y, CYAN)
                last_draw = now
            time.sleep(0.005)
    finally:
        touch.close()
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

