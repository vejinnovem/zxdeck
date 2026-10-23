#!/usr/bin/env python3
"""Interactive ZX Deck application shell for the tested TFT and touchscreen.

The tape library is real. Transport actions still stop at the backend boundary
until tape parsing and the isolated audio worker are connected.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import signal
import subprocess
import time

from zxdeck.config import AppConfig
from zxdeck.audio import AudioPlayer
from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import Screen, TouchRenderer, TouchUIController
from zxdeck.frontends.touch.frame import image_to_rgb565
from zxdeck.frontends.touch.splash import render_splash
from zxdeck.hardware.calibration import TouchCalibration
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341
from zxdeck.hardware.xpt2046 import XPT2046
from zxdeck.storage import (
    DirectoryBrowser,
    StorageUnavailable,
    TapeLibrary,
    load_selected_path,
    save_selected_path,
)


ROOT = Path(__file__).parents[1]
DEFAULT_CONFIG = ROOT / "config" / "hardware.zxdeck-pi-zero.toml"
DEFAULT_APP_CONFIG = ROOT / "config" / "application.zxdeck-pi-zero.toml"
DEFAULT_FONT = ROOT / "assets" / "fonts" / "bescii.ttf"
DEFAULT_STORAGE_STATE = Path("~/.local/state/zxdeck/storage-path").expanduser()

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
    parser.add_argument("--app-config", type=Path, default=DEFAULT_APP_CONFIG)
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_STORAGE_STATE)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--no-splash", action="store_true")
    parser.add_argument(
        "--mock-files",
        action="store_true",
        help="use built-in filenames only when the configured library is unavailable",
    )
    parser.add_argument(
        "--allow-poweroff",
        action="store_true",
        help="allow the confirmed Power Off action to shut down the OS",
    )
    return parser.parse_args()


def load_tape_entries(config):
    library = TapeLibrary(config)
    try:
        return library.refresh()
    except StorageUnavailable as exc:
        print(f"Tape library unavailable ({exc}).", flush=True)
        return ()


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


def send_pressed_feedback(display: ILI9341, rendered, action: str) -> None:
    """Invert only the touched target so feedback reaches the LCD immediately."""
    from PIL import ImageOps

    target = next(
        (item for item in reversed(rendered.targets) if item.action == action),
        None,
    )
    if target is None:
        return
    left, top, right, bottom = target.rect
    pressed = ImageOps.invert(rendered.image.crop(target.rect))
    display.set_window(left, top, right - 1, bottom - 1)
    display.write_rgb565(image_to_rgb565(pressed))


def main() -> int:
    args = parse_args()
    config = HardwareConfig.load(args.config)
    app_config = AppConfig.load(args.app_config)
    selected_storage_path = load_selected_path(
        args.storage_state,
        app_config.storage.path,
        app_config.storage.browse_root,
    )
    storage_config = replace(app_config.storage, path=selected_storage_path)
    calibration_path = args.calibration or config.touch.calibration_file
    if calibration_path is None:
        raise SystemExit("a calibration file is required")
    calibration = TouchCalibration.load(calibration_path)

    renderer = TouchRenderer(font_path=args.font if args.font.exists() else None)
    display = ILI9341(config.display)
    touch = XPT2046(config.touch)

    tape_entries = load_tape_entries(storage_config)
    tape_names = tuple(entry.name for entry in tape_entries)
    tape_paths = tuple(entry.path for entry in tape_entries)
    if not tape_names and args.mock_files:
        tape_names = MOCK_FILES
        tape_paths = ()
    controller = TouchUIController(
        tape_names,
        file_paths=tape_paths or None,
        state=DeckState(
            transport=TransportState.STOPPED,
            error=None if tape_names else "NO TAPE FILES",
        ),
        directory_browser=DirectoryBrowser(
            storage_config.browse_root,
            selected_storage_path
            if selected_storage_path.is_dir()
            else storage_config.browse_root,
        ),
    )
    rendered = None
    player = AudioPlayer(app_config.audio.playback_device)
    running = True
    cursor_visible = True
    cursor_changed_at = time.monotonic()

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    def redraw() -> None:
        nonlocal rendered
        rendered = controller.render(renderer, cursor_visible=cursor_visible)
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
            now = time.monotonic()
            playback_event = player.poll()
            if playback_event is not None:
                if playback_event.kind in {"finished", "stopped", "error"}:
                    controller.state = controller.state.next_revision(
                        transport=TransportState.STOPPED,
                        error=(
                            playback_event.message[:28].upper()
                            if playback_event.kind == "error"
                            else None
                        ),
                    )
                    redraw()
            if not touch.pressed:
                if controller.screen in {Screen.FILENAME, Screen.SEARCH}:
                    if controller.editor.expire(now=now):
                        cursor_visible = True
                        cursor_changed_at = now
                        redraw()
                    elif (
                        not controller.editor.has_pending_character
                        and now - cursor_changed_at >= 0.5
                    ):
                        cursor_visible = not cursor_visible
                        cursor_changed_at = now
                        redraw()
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

            send_pressed_feedback(display, rendered, action)
            wait_for_release()
            previous_storage_path = controller.selected_storage_path
            previous_transport = controller.state.transport
            controller.handle_action(action)

            if action == "play" and controller.state.transport is TransportState.PLAYING:
                tape_path = controller.selected_tape_path
                if tape_path is None:
                    controller.state = controller.state.next_revision(
                        transport=TransportState.STOPPED,
                        error="TAPE PATH UNAVAILABLE",
                    )
                else:
                    player.play(tape_path)
            elif (
                action in {"stop", "rewind", "new", "record"}
                or controller.state.transport is not previous_transport
                and controller.state.transport is not TransportState.PLAYING
            ):
                player.stop()
            cursor_visible = True
            cursor_changed_at = time.monotonic()
            redraw()

            if (
                controller.selected_storage_path is not None
                and controller.selected_storage_path != previous_storage_path
            ):
                save_selected_path(
                    args.storage_state,
                    controller.selected_storage_path,
                )
                selected_config = replace(
                    app_config.storage,
                    path=controller.selected_storage_path,
                )
                tape_entries = load_tape_entries(selected_config)
                controller.files = tuple(entry.name for entry in tape_entries)
                controller.file_paths = tuple(entry.path for entry in tape_entries)
                controller.search_query = ""

            if controller.shutdown_requested:
                if args.allow_poweroff:
                    print("Confirmed system poweroff.", flush=True)
                    time.sleep(0.5)
                    subprocess.run(
                        ("sudo", "-n", "systemctl", "poweroff"),
                        check=True,
                    )
                    running = False
                else:
                    print(
                        "Poweroff requested but --allow-poweroff is not enabled.",
                        flush=True,
                    )
                    time.sleep(0.5)
                    controller.shutdown_requested = False
                    controller.screen = Screen.SETTINGS
                    redraw()

    finally:
        player.close()
        touch.close()
        display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
