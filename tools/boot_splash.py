#!/usr/bin/env python3
"""Draw the ZX Deck branding image as early as practical during boot."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import socket
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
        default=20.0,
        help="maximum time to wait until SPI/GPIO devices are usable during early boot",
    )
    parser.add_argument(
        "--hold",
        action="store_true",
        help="keep the LCD reset line active until systemd stops this process",
    )
    return parser.parse_args()


def notify_systemd_ready() -> None:
    """Notify a Type=notify unit without adding a systemd Python dependency."""
    address = os.environ.get("NOTIFY_SOCKET")
    if not address:
        return
    if address.startswith("@"):
        address = "\0" + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
        notifier.connect(address)
        notifier.sendall(b"READY=1")


def wait_for_devices(config, timeout: float) -> None:
    required = (
        Path(f"/dev/spidev{config.spi_bus}.{config.spi_device}"),
        Path("/dev/gpiochip0"),
    )
    deadline = time.monotonic() + max(0.0, timeout)
    unavailable: dict[Path, str] = {}
    while True:
        unavailable.clear()
        for path in required:
            try:
                descriptor = os.open(path, os.O_RDWR | os.O_CLOEXEC)
            except OSError as error:
                unavailable[path] = str(error)
            else:
                os.close(descriptor)
        if not unavailable:
            return
        if time.monotonic() >= deadline:
            break
        time.sleep(0.05)
    details = ", ".join(f"{path}: {error}" for path, error in unavailable.items())
    raise SystemExit("boot splash hardware is not usable: " + details)


def main() -> int:
    args = parse_args()
    config = HardwareConfig.load(args.config)
    if not config.display.enabled:
        print("ZX Deck boot splash skipped: display is disabled.", flush=True)
        return 0

    wait_for_devices(config.display, args.wait_seconds)
    display = ILI9341(config.display)
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        display.initialize()
        image = render_splash(config.display.width, config.display.height)
        display.set_window(0, 0, config.display.width - 1, config.display.height - 1)
        display.write_rgb565(image_to_rgb565(image))
        notify_systemd_ready()
        print("ZX Deck boot splash displayed.", flush=True)
        while args.hold and running:
            time.sleep(0.1)
    finally:
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
