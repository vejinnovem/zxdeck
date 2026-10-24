#!/usr/bin/env python3
"""Interactive ZX Deck application for the tested TFT and touchscreen."""

from __future__ import annotations

import argparse
from dataclasses import replace
import os
from pathlib import Path
import signal
import subprocess
import time

from zxdeck.config import AppConfig
from zxdeck.audio import AudioPlayer, AudioSelection, list_audio_devices, load_audio_selection, save_audio_selection
from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import DeviceTouchRenderer, Screen, TouchUIController
from zxdeck.frontends.touch.frame import crop_rgb565, image_to_rgb565
from zxdeck.frontends.touch.renderer import TAPE_TITLE_RECT, marquee_offset
from zxdeck.frontends.touch.splash import render_splash
from zxdeck.hardware.calibration import TouchCalibration
from zxdeck.hardware.config import HardwareConfig
from zxdeck.hardware.ili9341 import ILI9341
from zxdeck.hardware.xpt2046 import XPT2046
from zxdeck.storage import DirectoryBrowser, StorageUnavailable, TapeLibrary, load_selected_path, save_selected_path
from zxdeck.system import apply_update, check_for_update, restart_zxdeck_service

ROOT = Path(__file__).parents[1]
DEFAULT_CONFIG = ROOT / "config" / "hardware.zxdeck-pi-zero.toml"
DEFAULT_APP_CONFIG = ROOT / "config" / "application.zxdeck-pi-zero.toml"
DEFAULT_FONT = ROOT / "assets" / "fonts" / "bescii.ttf"
DEFAULT_STORAGE_STATE = Path("~/.local/state/zxdeck/storage-path").expanduser()
DEFAULT_AUDIO_STATE = Path("~/.local/state/zxdeck/audio.json").expanduser()
DEFAULT_CALIBRATION_STATE = Path("~/.local/state/zxdeck/touch-calibration.json").expanduser()
HOME_PROGRESS_RECT = (10, 78, 230, 120)

MOCK_FILES = ("MANIC MINER.TZX", "JET SET WILLY.TAP", "ELITE.TZX", "DIZZY 3.TZX", "HEAD OVER HEELS.TZX", "SABOTEUR.TAP", "R-TYPE.TZX")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--app-config", type=Path, default=DEFAULT_APP_CONFIG)
    parser.add_argument("--storage-state", type=Path, default=DEFAULT_STORAGE_STATE)
    parser.add_argument("--audio-state", type=Path, default=DEFAULT_AUDIO_STATE)
    parser.add_argument("--calibration", type=Path)
    parser.add_argument("--font", type=Path, default=DEFAULT_FONT)
    parser.add_argument("--no-splash", action="store_true")
    parser.add_argument("--mock-files", action="store_true", help="use built-in filenames only when the configured library is unavailable")
    parser.add_argument("--allow-poweroff", action="store_true", help="allow the confirmed Power Off action to shut down the OS")
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
        raise ValueError(f"UI frame is {image.size}, display is {display.config.width}x{display.config.height}")
    display.set_window(0, 0, display.config.width - 1, display.config.height - 1)
    display.write_rgb565(image_to_rgb565(image))


def send_frame(display: ILI9341, rendered) -> None:
    send_image(display, rendered.image)


def send_tape_title(display: ILI9341, title_pixels: bytes) -> None:
    left, top, right, bottom = TAPE_TITLE_RECT
    display.set_window(left, top, right - 1, bottom - 1)
    display.write_rgb565(title_pixels)


def send_region(display: ILI9341, image, rect: tuple[int, int, int, int]) -> None:
    """Send only one rectangular UI region instead of repainting the full TFT."""
    left, top, right, bottom = rect
    display.set_window(left, top, right - 1, bottom - 1)
    display.write_rgb565(image_to_rgb565(image.crop(rect)))


def send_pressed_feedback(display: ILI9341, rendered, action: str) -> None:
    from PIL import ImageOps
    target = next((item for item in reversed(rendered.targets) if item.action == action), None)
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
    audio_selection = load_audio_selection(args.audio_state, default_playback=app_config.audio.playback_device, default_capture=app_config.audio.capture_device)
    selected_storage_path = load_selected_path(args.storage_state, app_config.storage.path, app_config.storage.browse_root)
    storage_config = replace(app_config.storage, path=selected_storage_path)

    if args.calibration is not None:
        calibration_path = args.calibration.expanduser()
    elif DEFAULT_CALIBRATION_STATE.exists():
        calibration_path = DEFAULT_CALIBRATION_STATE
    else:
        calibration_path = config.touch.calibration_file
    if calibration_path is None:
        raise SystemExit("a calibration file is required")
    calibration = TouchCalibration.load(calibration_path)

    renderer = DeviceTouchRenderer(font_path=args.font if args.font.exists() else None)
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
        state=DeckState(transport=TransportState.STOPPED, error=None if tape_names else "NO TAPE FILES"),
        directory_browser=DirectoryBrowser(storage_config.browse_root, selected_storage_path if selected_storage_path.is_dir() else storage_config.browse_root),
        selected_storage_path=selected_storage_path,
        playback_devices=list_audio_devices("playback"),
        capture_devices=list_audio_devices("capture"),
        selected_playback_device=audio_selection.playback_device,
        selected_capture_device=audio_selection.capture_device,
        output_level=audio_selection.output_level,
        previous_output_level=max(5, audio_selection.output_level),
    )
    rendered = None
    player = AudioPlayer(audio_selection.playback_device, output_level=audio_selection.output_level)
    running = True
    cursor_visible = True
    cursor_changed_at = time.monotonic()
    title_name = None
    title_started_at = time.monotonic()
    title_offset = 0
    previous_screen = None
    title_refresh_at = 0.0
    title_rgb565 = b""
    title_canvas_width = 0
    playback_phase = None
    progress_animation_step = 0

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    def redraw() -> None:
        nonlocal rendered, previous_screen, title_name, title_started_at, title_offset, title_rgb565, title_canvas_width
        current_title = controller.state.tape_name or "NO TAPE"
        if controller.screen is Screen.HOME and (previous_screen is not Screen.HOME or current_title != title_name):
            title_name = current_title
            title_started_at = time.monotonic()
            title_offset = 0
            title_canvas = renderer.tape_title_canvas(current_title)
            title_canvas_width = title_canvas.width
            title_rgb565 = image_to_rgb565(title_canvas)
        rendered = controller.render(renderer, cursor_visible=cursor_visible)
        if controller.screen is Screen.HOME and controller.state.transport is TransportState.PLAYING:
            renderer.decorate_signal_progress(
                rendered.image,
                controller.state,
                phase=playback_phase,
                animation_step=progress_animation_step,
            )
        send_frame(display, rendered)
        previous_screen = controller.screen

    def redraw_home_progress() -> None:
        """Refresh only progress/time pixels so title scrolling is not stalled."""
        nonlocal rendered
        if controller.screen is not Screen.HOME:
            return
        fresh = controller.render(renderer, cursor_visible=cursor_visible)
        renderer.decorate_signal_progress(
            fresh.image,
            controller.state,
            phase=playback_phase,
            animation_step=progress_animation_step,
        )
        send_region(display, fresh.image, HOME_PROGRESS_RECT)
        if rendered is None:
            rendered = fresh
        else:
            rendered.image.paste(
                fresh.image.crop(HOME_PROGRESS_RECT),
                HOME_PROGRESS_RECT[:2],
            )

    def wait_for_release() -> None:
        while running and touch.pressed:
            time.sleep(0.01)
        time.sleep(0.03)

    def save_audio_state() -> None:
        save_audio_selection(args.audio_state, AudioSelection(controller.selected_playback_device, controller.selected_capture_device, controller.output_level))

    def show_update_result(result) -> None:
        controller.update_installed_version = result.local_commit
        controller.update_available_version = result.remote_commit
        controller.update_status = result.message
        controller.update_can_install = result.can_install
        controller.update_busy = False
        print(f"Updater: {result.message}" + (f": {result.detail}" if result.detail else ""), flush=True)

    def check_updates() -> None:
        controller.update_busy = True
        controller.update_status = "CHECKING..."
        controller.update_can_install = False
        redraw()
        show_update_result(check_for_update(ROOT))
        redraw()

    def install_update() -> None:
        if not controller.update_can_install:
            return
        player.stop()
        if controller.state.transport is not TransportState.STOPPED:
            controller.state = controller.state.next_revision(transport=TransportState.STOPPED)
        controller.update_busy = True
        controller.update_status = "INSTALLING..."
        controller.update_can_install = False
        redraw()
        result = apply_update(ROOT)
        show_update_result(result)
        if not result.updated:
            redraw()
            return
        if not os.environ.get("INVOCATION_ID"):
            controller.update_status = "INSTALLED - RESTART APP"
            controller.update_busy = False
            redraw()
            print("Update installed, but this process was not started by systemd; restart ZX Deck manually.", flush=True)
            return
        controller.update_busy = True
        controller.update_status = "RESTARTING..."
        redraw()
        print("Update installed; restarting zxdeck.service.", flush=True)
        time.sleep(0.4)
        restarted, detail = restart_zxdeck_service()
        if restarted:
            return
        controller.update_busy = False
        controller.update_status = "INSTALLED - RESTART NEEDED"
        if detail:
            print(f"ZX Deck restart failed: {detail}", flush=True)
        redraw()

    def apply_action(action: str, *, persist_audio: bool = True) -> None:
        nonlocal running, cursor_visible, cursor_changed_at, tape_entries, playback_phase, progress_animation_step
        previous_storage_path = controller.selected_storage_path
        previous_transport = controller.state.transport
        previous_playback_device = controller.selected_playback_device
        previous_capture_device = controller.selected_capture_device
        previous_output_level = controller.output_level
        if action == "playback-device":
            controller.playback_devices = list_audio_devices("playback")
        elif action == "capture-device":
            controller.capture_devices = list_audio_devices("capture")
        controller.handle_action(action)
        if action in {"updates", "check-update"}:
            check_updates(); return
        if action == "install-update":
            install_update(); return
        if action == "play" and controller.state.transport is TransportState.PLAYING:
            tape_path = controller.selected_tape_path
            playback_phase = None
            progress_animation_step = 0
            if tape_path is None:
                controller.state = controller.state.next_revision(transport=TransportState.STOPPED, error="TAPE PATH UNAVAILABLE")
            else:
                player.play(tape_path)
        elif action in {"stop", "rewind", "new", "record"} or controller.state.transport is not previous_transport and controller.state.transport is not TransportState.PLAYING:
            player.stop()
            playback_phase = None
        audio_changed = controller.selected_playback_device != previous_playback_device or controller.selected_capture_device != previous_capture_device or controller.output_level != previous_output_level
        if controller.selected_playback_device != previous_playback_device:
            player.device = controller.selected_playback_device
        if controller.output_level != previous_output_level:
            player.set_output_level(controller.output_level)
        if audio_changed and persist_audio:
            save_audio_state()
            print(f"Audio settings saved: playback={controller.selected_playback_device} capture={controller.selected_capture_device} level={controller.output_level}%", flush=True)
        if controller.selected_storage_path is not None and controller.selected_storage_path != previous_storage_path:
            save_selected_path(args.storage_state, controller.selected_storage_path)
            selected_config = replace(app_config.storage, path=controller.selected_storage_path)
            tape_entries = load_tape_entries(selected_config)
            controller.files = tuple(entry.name for entry in tape_entries)
            controller.file_paths = tuple(entry.path for entry in tape_entries)
            controller.search_query = ""
        cursor_visible = True
        cursor_changed_at = time.monotonic()
        redraw()
        if controller.shutdown_requested:
            if args.allow_poweroff:
                print("Confirmed system poweroff.", flush=True)
                time.sleep(0.5)
                subprocess.run(("sudo", "-n", "systemctl", "poweroff"), check=True)
                running = False
            else:
                print("Poweroff requested but --allow-poweroff is not enabled.", flush=True)
                time.sleep(0.5)
                controller.shutdown_requested = False
                controller.screen = Screen.SETTINGS
                redraw()

    def handle_repeatable_touch(action: str) -> bool:
        screen = controller.screen
        if screen is Screen.FILES and action in {"up", "down"}:
            apply_action(action); started = time.monotonic(); next_repeat = started + 1.0
            while running and touch.pressed:
                now = time.monotonic()
                if now >= next_repeat:
                    elapsed = now - started; repeat_action = action; interval = 0.14
                    if elapsed >= 2.5:
                        repeat_action = "group-up" if action == "up" else "group-down"; interval = 0.35
                    apply_action(repeat_action); next_repeat = now + interval
                time.sleep(0.01)
            time.sleep(0.03); return True
        if screen is Screen.SETTINGS and action in {"settings-up", "settings-down"}:
            apply_action(action); started = time.monotonic(); next_repeat = started + 1.0
            while running and touch.pressed:
                now = time.monotonic()
                if now >= next_repeat:
                    apply_action(action); next_repeat = now + 0.18
                time.sleep(0.01)
            time.sleep(0.03); return True
        if screen is Screen.OUTPUT_LEVEL and action in {"volume-up", "volume-down"}:
            apply_action(action, persist_audio=False); started = time.monotonic(); next_repeat = started + 0.6
            while running and touch.pressed:
                now = time.monotonic()
                if now >= next_repeat:
                    apply_action(action, persist_audio=False); next_repeat = now + 0.18
                time.sleep(0.01)
            save_audio_state(); time.sleep(0.03); return True
        return False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        display.initialize()
        if not args.no_splash:
            send_image(display, render_splash(config.display.width, config.display.height)); time.sleep(0.8)
        redraw()
        print("ZX Deck interactive UI prototype ready. Press Ctrl+C to stop.", flush=True)
        while running:
            playback_event = player.poll()
            if playback_event is not None:
                if playback_event.kind in {"started", "progress"}:
                    controller.state = controller.state.next_revision(transport=TransportState.PLAYING, position_seconds=playback_event.position_seconds if playback_event.position_seconds is not None else controller.state.position_seconds, duration_seconds=playback_event.duration_seconds if playback_event.duration_seconds is not None else controller.state.duration_seconds, error=None)
                    if playback_event.kind == "progress" and playback_event.phase is not None:
                        playback_phase = playback_event.phase
                        progress_animation_step += 1
                elif playback_event.kind in {"finished", "stopped", "error"}:
                    playback_phase = None
                    controller.state = controller.state.next_revision(transport=TransportState.STOPPED, position_seconds=playback_event.position_seconds if playback_event.position_seconds is not None else controller.state.position_seconds, duration_seconds=playback_event.duration_seconds if playback_event.duration_seconds is not None else controller.state.duration_seconds, error=playback_event.message[:28].upper() if playback_event.kind == "error" else None)
                if controller.screen is Screen.HOME:
                    if playback_event.kind == "progress":
                        redraw_home_progress()
                    else:
                        redraw()
            now = time.monotonic()
            if controller.screen is Screen.HOME and now >= title_refresh_at:
                current_title = controller.state.tape_name or "NO TAPE"
                maximum_offset = max(0, renderer.tape_title_width(current_title) - (TAPE_TITLE_RECT[2] - TAPE_TITLE_RECT[0]))
                next_offset = marquee_offset(now - title_started_at, maximum_offset)
                if next_offset != title_offset:
                    title_image = renderer.render_tape_title(current_title, offset=next_offset)
                    title_width = TAPE_TITLE_RECT[2] - TAPE_TITLE_RECT[0]; title_height = TAPE_TITLE_RECT[3] - TAPE_TITLE_RECT[1]
                    title_pixels = crop_rgb565(title_rgb565, title_canvas_width, next_offset, 0, title_width, title_height)
                    send_tape_title(display, title_pixels)
                    if rendered is not None:
                        rendered.image.paste(title_image, TAPE_TITLE_RECT[:2])
                    title_offset = next_offset
                title_refresh_at = now + 0.1
            if not touch.pressed:
                if controller.screen in {Screen.FILENAME, Screen.SEARCH}:
                    if controller.editor.expire(now=now):
                        cursor_visible = True; cursor_changed_at = now; redraw()
                    elif not controller.editor.has_pending_character and now - cursor_changed_at >= 0.5:
                        cursor_visible = not cursor_visible; cursor_changed_at = now; redraw()
                time.sleep(0.01); continue
            raw_x, raw_y = touch.read_raw()
            x, y = calibration.map(raw_x, raw_y, config.display.width, config.display.height)
            action = rendered.action_at(x, y) if rendered is not None else None
            if action is None:
                wait_for_release(); continue
            print(f"touch x={x:3d} y={y:3d} action={action}", flush=True)
            send_pressed_feedback(display, rendered, action)
            if handle_repeatable_touch(action):
                continue
            wait_for_release(); apply_action(action)
    finally:
        player.close(); touch.close(); display.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
