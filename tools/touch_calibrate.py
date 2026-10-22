#!/usr/bin/env python3
"""Run guided five-point XPT2046 calibration and save device state."""

from __future__ import annotations

import argparse
from pathlib import Path
import signal
import statistics
import time

from zxdeck.hardware.calibration import TouchCalibration, fit_calibration
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341
from zxdeck.hardware.xpt2046 import XPT2046


DEFAULT_CONFIG = Path(__file__).parents[1] / "config" / "hardware.zxdeck-pi-zero.toml"
DEFAULT_OUTPUT = Path.home() / ".local" / "state" / "zxdeck" / "touch-calibration.json"
BLACK, WHITE, RED, GREEN = 0x0000, 0xFFFF, 0xF800, 0x07E0
TARGET_TOLERANCE = 60


def draw_border(display: ILI9341) -> None:
    width, height = display.config.width, display.config.height
    display.fill_rect(0, 0, width, 2, WHITE)
    display.fill_rect(0, height - 2, width, 2, WHITE)
    display.fill_rect(0, 0, 2, height, WHITE)
    display.fill_rect(width - 2, 0, 2, height, WHITE)


def draw_target(display: ILI9341, target: tuple[int, int], color: int) -> None:
    x, y = target
    display.fill_rect(x - 10, y - 2, 21, 5, color)
    display.fill_rect(x - 2, y - 10, 5, 21, color)


def wait_for(touch: XPT2046, pressed: bool, running: list[bool]) -> None:
    while running[0] and touch.pressed != pressed:
        time.sleep(0.01)
    if not running[0]:
        raise KeyboardInterrupt


def capture_press(touch: XPT2046, running: list[bool]) -> tuple[int, int]:
    wait_for(touch, False, running)
    wait_for(touch, True, running)
    time.sleep(0.04)
    xs: list[int] = []
    ys: list[int] = []
    deadline = time.monotonic() + 0.6
    while running[0] and touch.pressed and time.monotonic() < deadline:
        x, y = touch.read_raw()
        if 1 <= x <= 4094 and 1 <= y <= 4094:
            xs.append(x)
            ys.append(y)
        time.sleep(0.01)
    wait_for(touch, False, running)
    if not xs:
        raise RuntimeError("touch produced no valid samples")
    return int(statistics.median(xs)), int(statistics.median(ys))


def capture_target(
    display: ILI9341,
    touch: XPT2046,
    running: list[bool],
    target: tuple[int, int],
    prior: TouchCalibration | None,
) -> tuple[int, int]:
    while True:
        sample = capture_press(touch, running)
        if prior is None:
            return sample
        mapped = prior.map(*sample, display.config.width, display.config.height)
        error = ((mapped[0] - target[0]) ** 2 + (mapped[1] - target[1]) ** 2) ** 0.5
        if error <= TARGET_TOLERANCE:
            return sample
        print(
            f"Rejected raw={sample}, mapped={mapped}, error={error:.1f}px",
            flush=True,
        )
        draw_target(display, target, RED)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--prior", type=Path)
    args = parser.parse_args()
    config = HardwareConfig.load(args.config)
    prior_path = args.prior or config.touch.calibration_file
    prior = TouchCalibration.load(prior_path) if prior_path and prior_path.exists() else None

    width, height = config.display.width, config.display.height
    targets = [(20, 20), (width - 21, 20), (width - 21, height - 21), (20, height - 21), (width // 2, height // 2)]
    display = ILI9341(config.display)
    touch = XPT2046(config.touch)
    running = [True]

    def stop(_signum: int, _frame: object) -> None:
        running[0] = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        display.initialize()
        samples: list[tuple[int, int]] = []
        for index, target in enumerate(targets, 1):
            display.fill(BLACK)
            draw_border(display)
            draw_target(display, target, RED)
            print(f"Target {index}/{len(targets)} at {target}", flush=True)
            sample = capture_target(display, touch, running, target, prior)
            samples.append(sample)
            draw_target(display, target, GREEN)
            print(f"Captured raw={sample}", flush=True)
            time.sleep(0.25)

        for _attempt in range(3):
            calibration, rejected = fit_calibration(targets, samples)
            if not rejected:
                break
            for index in sorted(rejected):
                target = targets[index]
                display.fill(BLACK)
                draw_border(display)
                draw_target(display, target, RED)
                print(f"Repeat rejected target {index + 1} at {target}", flush=True)
                samples[index] = capture_target(display, touch, running, target, prior)
        else:
            raise RuntimeError("calibration remained inconsistent after retries")

        calibration.save(args.output)
        print(f"Saved calibration to {args.output.expanduser()}", flush=True)
        display.fill(BLACK)
        draw_border(display)
        draw_target(display, (width // 2, height // 2), GREEN)
        while running[0]:
            if touch.pressed:
                raw = touch.read_raw()
                point = calibration.map(*raw, width, height)
                draw_target(display, point, GREEN)
            time.sleep(0.01)
    finally:
        touch.close()
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

