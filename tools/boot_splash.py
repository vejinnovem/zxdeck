#!/usr/bin/env python3
"""Draw the ZX Deck branding image as early as practical during boot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time


ROOT = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(ROOT / "src"))

from zxdeck.frontends.touch.frame import image_to_rgb565
from zxdeck.frontends.touch.splash import render_splash
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341


DEFAULT_CONFIG = ROOT / "config" / "hardware.zxdeck-pi-zero.toml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=3.0,
        help="maximum time to wait for SPI/GPIO device nodes during early boot",
    )
    return parser.parse_args()


def wait_for_devices(config, timeout: float) -> None:
    required = (
        Path(f"/dev/spidev{config.spi_bus}.{config.spi_device}"),
        Path("/dev/gpiochip0"),
    )
    deadline = time.monotonic() + max(0.0, timeout)
    while time.monotonic() < deadline:
        missing = [path for path in required if not path.exists()]
        if not missing:
            return
        time.sleep(0.05)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("boot splash hardware did not appear: " + ", ".join(missing))


def main() -> int:
    args = parse_args()
    config = HardwareConfig.load(args.config)
    if not config.display.enabled:
        print("ZX Deck boot splash skipped: display is disabled.", flush=True)
        return 0

    wait_for_devices(config.display, args.wait_seconds)
    display = ILI9341(config.display)
    try:
        display.initialize()
        image = render_splash(config.display.width, config.display.height)
        display.set_window(0, 0, config.display.width - 1, config.display.height - 1)
        display.write_rgb565(image_to_rgb565(image))
    finally:
        display.close()

    print("ZX Deck boot splash displayed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
