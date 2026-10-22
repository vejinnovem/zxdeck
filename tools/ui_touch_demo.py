#!/usr/bin/env python3
"""Interactive ZX Deck UI prototype for the tested 240x320 TFT and XPT2046.

This is deliberately a frontend/ergonomics demo. Transport actions only mutate
mock DeckState data; they do not access audio, tape parsing or storage.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import signal
import time

from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import MultiTapEditor, Screen, TouchRenderer
from zxdeck.frontends.touch.frame import image_to_rgb565
from zxdeck.frontends.touch.splash import render_splash
from zxdeck.hardware.calibration import TouchCalibration
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341
from zxdeck.hardware.xpt2046 import XPT2046


ROOT = Path(__file__).parents[1]
DEFAULT_CONFIG = ROOT / "config" / "hardware.zxdeck-pi-zero.toml"
DEFAULT_FONT = ROOT / "assets" / "fonts" / "bescii.ttf"

MOCK_FILES = (
    "MANIC MINER.TZX",
    "JET SET WILLY.TAP",
    "ELITE.TZX",
    "DIZZY 3.TZX",
    "HEAD OVER HEELS.TZX",
    "SABOTEUR.TAP",
    "R-TYPE.TZX",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--no-splash", action="store_true")
    return parser.parse_args()


def send_image(display: ILI9341, image) -> None:
    if image.size != (display.config.width, display.config.height):
        raise ValueError(
            f"UI frame is {image.size}, display is "
            f"{display.config.width}x{display.config.height}"
        )
    display.set_window(0, 0, display.config.width - 1, display.config.height - 1)
    display.write_rgb565(image_to_rgb565(image))


def send_frame(display: ILI9341, rendered) -> None:
    send_image(display, rendered.image)


def main() -> int:
    args = parse_args()
    config = HardwareConfig.load(args.config)
    calibration_path = args.calibration or config.touch.calibration_file
    if calibration_path is None:
        raise SystemExit("a calibration file is required")
    calibration = TouchCalibration.load(calibration_path)

    renderer = TouchRenderer(font_path=args.font if args.font.exists() else None)
    display = ILI9341(config.display)
    touch = XPT2046(config.touch)

    state = DeckState(
        transport=TransportState.STOPPED,
        tape_name="MANIC MINER.TZX",
        position_seconds=102,
        duration_seconds=196,
    )
    screen = Screen.HOME
    selected_file = 0
    editor = MultiTapEditor()
    rendered = None
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    def redraw() -> None:
        nonlocal rendered
        if screen is Screen.HOME:
            rendered = renderer.render_home(state)
        elif screen is Screen.FILES:
            rendered = renderer.render_files(MOCK_FILES, selected=selected_file)
        elif screen is Screen.FILENAME:
            rendered = renderer.render_filename(editor)
        else:
            rendered = renderer.render_settings()
        send_frame(display, rendered)

    def wait_for_release() -> None:
        while running and touch.pressed:
            time.sleep(0.01)
        time.sleep(0.03)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        display.initialize()
        if not args.no_splash:
            send_image(
                display,
                render_splash(config.display.width, config.display.height),
            )
            time.sleep(0.8)
        redraw()
        print("ZX Deck interactive UI prototype ready. Press Ctrl+C to stop.", flush=True)

        while running:
            if screen is Screen.FILENAME and editor.expire():
                redraw()

            if not touch.pressed:
                time.sleep(0.01)
                continue

            raw_x, raw_y = touch.read_raw()
            x, y = calibration.map(
                raw_x, raw_y, config.display.width, config.display.height
            )
            action = rendered.action_at(x, y) if rendered is not None else None
            if action is None:
                wait_for_release()
                continue

            print(f"touch x={x:3d} y={y:3d} action={action}", flush=True)

            if screen is Screen.HOME:
                if action == "files":
                    screen = Screen.FILES
                elif action == "new":
                    editor = MultiTapEditor()
                    screen = Screen.FILENAME
                elif action == "settings":
                    screen = Screen.SETTINGS
                elif action == "play":
                    state = state.next_revision(transport=TransportState.PLAYING)
                elif action == "stop":
                    state = state.next_revision(transport=TransportState.STOPPED)
                elif action == "record":
                    state = state.next_revision(transport=TransportState.RECORDING)
                elif action == "rewind":
                    state = state.next_revision(position_seconds=0.0)

            elif screen is Screen.FILES:
                if action == "back":
                    screen = Screen.HOME
                elif action == "up":
                    selected_file = max(0, selected_file - 1)
                elif action == "open-selected":
                    state = state.next_revision(tape_name=MOCK_FILES[selected_file])
                    screen = Screen.HOME
                elif action.startswith("open:"):
                    selected_file = int(action.split(":", 1)[1])
                    state = state.next_revision(tape_name=MOCK_FILES[selected_file])
                    screen = Screen.HOME

            elif screen is Screen.FILENAME:
                if action == "cancel":
                    screen = Screen.HOME
                elif action == "save":
                    name = editor.text.strip() or "UNTITLED"
                    if "." not in Path(name).name:
                        name += ".TZX"
                    state = state.next_revision(tape_name=name)
                    screen = Screen.HOME
                elif action.startswith("key:"):
                    editor.press(action.split(":", 1)[1])

            elif screen is Screen.SETTINGS:
                if action == "back":
                    screen = Screen.HOME

            redraw()
            wait_for_release()

    finally:
        touch.close()
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
