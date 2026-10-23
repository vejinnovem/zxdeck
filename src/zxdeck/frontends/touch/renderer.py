"""240x320 device UI renderer.

Rendering targets an ordinary Pillow RGB image. Raspberry Pi display code is a
separate adapter concern: it can convert the completed frame to RGB565 and send
it through :class:`zxdeck.hardware.ili9341.ILI9341`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

from zxdeck.core.state import DeckState, TransportState

from .keypad import MultiTapEditor

if TYPE_CHECKING:
    from PIL.Image import Image


WIDTH = 240
HEIGHT = 320
TAPE_TITLE_RECT = (10, 38, 230, 73)

BLACK = (0, 0, 0)
WHITE = (245, 245, 245)
DIM = (105, 105, 105)
DARK = (24, 24, 24)
CYAN = (0, 205, 235)
YELLOW = (245, 220, 0)
GREEN = (0, 205, 70)
RED = (235, 45, 35)


class Screen(str, Enum):
    HOME = "home"
    FILES = "files"
    FILENAME = "filename"
    SEARCH = "search"
    LETTERS = "letters"
    SETTINGS = "settings"
    OUTPUT_LEVEL = "output_level"
    DIRECTORIES = "directories"
    AUDIO_PLAYBACK = "audio_playback"
    AUDIO_CAPTURE = "audio_capture"
    POWER = "power"


@dataclass(frozen=True, slots=True)
class HitTarget:
    action: str
    rect: tuple[int, int, int, int]

    def contains(self, x: int, y: int) -> bool:
        left, top, right, bottom = self.rect
        return left <= x < right and top <= y < bottom


@dataclass(frozen=True, slots=True)
class RenderedScreen:
    image: "Image"
    targets: tuple[HitTarget, ...] = ()

    def action_at(self, x: int, y: int) -> str | None:
        for target in reversed(self.targets):
            if target.contains(x, y):
                return target.action
        return None


class TouchRenderer:
    """Render the ZX Deck device UI without touching Raspberry Pi hardware."""

    def __init__(self, *, font_path: str | Path | None = None) -> None:
        self.font_path = Path(font_path) if font_path is not None else None
        self._fonts: dict[int, object] = {}
        self._tape_title_cache_name: str | None = None
        self._tape_title_cache_image = None

    def render_home(self, state: DeckState) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []

        self._header(draw, "ZX DECK", state.transport.value.upper())

        tape_name = state.tape_name or "NO TAPE"
        image.paste(self.render_tape_title(tape_name), TAPE_TITLE_RECT[:2])

        progress_left, progress_top, progress_right, progress_bottom = 16, 82, 224, 92
        draw.rectangle((progress_left, progress_top, progress_right, progress_bottom), outline=DIM)
        if state.duration_seconds and state.duration_seconds > 0:
            ratio = min(1.0, max(0.0, state.position_seconds / state.duration_seconds))
            fill_right = progress_left + int((progress_right - progress_left) * ratio)
            if fill_right > progress_left:
                draw.rectangle(
                    (progress_left + 1, progress_top + 1, fill_right, progress_bottom - 1),
                    fill=CYAN,
                )

        self._text(draw, self._format_time(state.position_seconds), (16, 100), size=10)
        duration = self._format_time(state.duration_seconds) if state.duration_seconds is not None else "--:--"
        self._right_text(draw, duration, 224, 100, size=10)

        transport = (
            ("rewind", "<<", 16),
            ("stop", "STOP", 86),
            ("play", "PLAY", 156),
        )
        for action, label, x in transport:
            rect = (x, 126, x + 58, 174)
            active = (
                (action == "play" and state.transport is TransportState.PLAYING)
                or (action == "stop" and state.transport is TransportState.STOPPED)
            )
            self._button(draw, rect, label, active=active, accent=CYAN)
            targets.append(HitTarget(action, rect))

        rec_rect = (62, 187, 178, 229)
        self._button(
            draw,
            rec_rect,
            "REC",
            active=state.transport is TransportState.RECORDING,
            accent=RED,
        )
        targets.append(HitTarget("record", rec_rect))

        if state.error:
            draw.rectangle((10, 238, 230, 265), outline=RED)
            self._center_text(draw, state.error[:28], 247, size=8, fill=RED)

        nav = (
            ("files", "FILES", 0, CYAN),
            ("new", "NEW", 80, YELLOW),
            ("settings", "SET", 160, GREEN),
        )
        for action, label, x, accent in nav:
            rect = (x, 276, x + 80, 320)
            self._button(draw, rect, label, accent=accent, squared=True)
            targets.append(HitTarget(action, rect))

        return RenderedScreen(image, tuple(targets))

    def tape_title_width(self, tape_name: str) -> int:
        return self.tape_title_canvas(tape_name).width

    def tape_title_canvas(self, tape_name: str):
        """Return the cached full-width title used by partial LCD updates."""
        return self._tape_title_canvas(tape_name)

    def render_tape_title(self, tape_name: str, *, offset: int = 0):
        """Render the clipped Home title strip for inexpensive marquee updates."""
        left, top, right, bottom = TAPE_TITLE_RECT
        width, height = right - left, bottom - top
        canvas = self._tape_title_canvas(tape_name)
        maximum_offset = max(0, canvas.width - width)
        left_offset = min(maximum_offset, max(0, offset))
        return canvas.crop((left_offset, 0, left_offset + width, height))

    def _tape_title_canvas(self, tape_name: str):
        if (
            tape_name == self._tape_title_cache_name
            and self._tape_title_cache_image is not None
        ):
            return self._tape_title_cache_image

        from PIL import Image, ImageDraw

        viewport_width = TAPE_TITLE_RECT[2] - TAPE_TITLE_RECT[0]
        height = TAPE_TITLE_RECT[3] - TAPE_TITLE_RECT[1]
        measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        font = self._font(16)
        box = measure.textbbox((0, 0), tape_name, font=font)
        text_width = box[2] - box[0]
        canvas = Image.new("RGB", (max(viewport_width, text_width), height), BLACK)
        draw = ImageDraw.Draw(canvas)
        x = (viewport_width - text_width) // 2 if text_width <= viewport_width else 0
        draw.text((x, 9), tape_name, font=font, fill=WHITE, spacing=0)
        self._tape_title_cache_name = tape_name
        self._tape_title_cache_image = canvas
        return canvas

    def render_files(
        self,
        files: Sequence[str],
        *,
        selected: int = 0,
        offset: int = 0,
        query: str = "",
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        title = "FILES" if not query else f"FILES:{query[:9]}"
        self._header(draw, title, f"{len(files)}")

        visible = files[offset : offset + 6]
        row_top = 32
        row_height = 38
        for index, filename in enumerate(visible):
            absolute_index = offset + index
            rect = (8, row_top + index * row_height, 232, row_top + index * row_height + 34)
            if absolute_index == selected:
                draw.rectangle(rect, fill=(30, 60, 65), outline=CYAN)
            else:
                draw.rectangle(rect, outline=(55, 55, 55))
            self._text(draw, filename[:25], (16, rect[1] + 10), size=10)
            targets.append(HitTarget(f"open:{absolute_index}", rect))

        back_rect = (0, 276, 60, 320)
        up_rect = (60, 276, 120, 320)
        down_rect = (120, 276, 180, 320)
        search_rect = (180, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(draw, up_rect, "UP", accent=YELLOW, squared=True)
        self._button(draw, down_rect, "DOWN", accent=YELLOW, squared=True)
        self._button(draw, search_rect, "FIND", accent=GREEN, squared=True)
        targets.extend(
            (
                HitTarget("back", back_rect),
                HitTarget("up", up_rect),
                HitTarget("down", down_rect),
                HitTarget("search", search_rect),
            )
        )
        return RenderedScreen(image, tuple(targets))

    def render_filename(
        self,
        editor: MultiTapEditor,
        *,
        cursor_visible: bool = True,
        title: str = "SAVE AS",
        accept_label: str = "SAVE",
        accept_action: str = "save",
        middle_label: str | None = None,
        middle_action: str | None = None,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, title, editor.mode.value)

        draw.rectangle((8, 32, 232, 67), outline=CYAN)
        show_cursor = cursor_visible and not editor.has_pending_character
        value = editor.text[-25:] + ("_" if show_cursor else "")
        self._text(draw, value, (14, 44), size=12)

        labels = {
            "1": ".,?!",
            "2": "ABC",
            "3": "DEF",
            "4": "GHI",
            "5": "JKL",
            "6": "MNO",
            "7": "PQRS",
            "8": "TUV",
            "9": "WXYZ",
            "*": "DEL",
            "0": " _-",
            "#": "MODE",
        }
        keys = ("1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#")
        x_positions = (6, 84, 162)
        y_positions = (78, 124, 170, 216)

        for index, key in enumerate(keys):
            col = index % 3
            row = index // 3
            rect = (x_positions[col], y_positions[row], x_positions[col] + 72, y_positions[row] + 40)
            draw.rectangle(rect, fill=DARK, outline=WHITE)
            self._center_text_in_rect(draw, key, rect, size=16, y_offset=-6)
            self._center_text_in_rect(draw, labels[key], rect, size=7, y_offset=10, fill=DIM)
            targets.append(HitTarget(f"key:{key}", rect))

        button_width = 80 if middle_label and middle_action else 120
        cancel_rect = (0, 270, button_width, 320)
        save_rect = (240 - button_width, 270, 240, 320)
        self._button(draw, cancel_rect, "CANCEL", accent=RED, squared=True)
        self._button(draw, save_rect, accept_label, accent=GREEN, squared=True)
        targets.append(HitTarget("cancel", cancel_rect))
        if middle_label and middle_action:
            middle_rect = (80, 270, 160, 320)
            self._button(draw, middle_rect, middle_label, accent=YELLOW, squared=True)
            targets.append(HitTarget(middle_action, middle_rect))
        targets.append(HitTarget(accept_action, save_rect))
        return RenderedScreen(image, tuple(targets))

    def render_search(
        self,
        editor: MultiTapEditor,
        *,
        cursor_visible: bool = True,
    ) -> RenderedScreen:
        return self.render_filename(
            editor,
            cursor_visible=cursor_visible,
            title="SEARCH",
            accept_label="FIND",
            accept_action="apply-search",
            middle_label="A-Z",
            middle_action="letters",
        )

    def render_letters(self) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "JUMP TO LETTER", "A-Z")

        for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ#"):
            column = index % 6
            row = index // 6
            rect = (
                column * 40 + 2,
                36 + row * 44,
                column * 40 + 38,
                76 + row * 44,
            )
            self._button(draw, rect, letter, accent=CYAN)
            targets.append(HitTarget(f"jump:{letter}", rect))

        back_rect = (0, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=YELLOW, squared=True)
        targets.append(HitTarget("back", back_rect))
        return RenderedScreen(image, tuple(targets))

    def render_settings(
        self,
        *,
        playback_device: str = "default",
        capture_device: str = "default",
        output_level: int = 25,
        offset: int = 0,
        ip_address: str = "NO NETWORK",
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "SETTINGS", "DEVICE")

        entries = (
            ("directories", "TAPE DIRECTORY", "", CYAN),
            ("playback-device", "PLAYBACK", self._short_device(playback_device), GREEN),
            ("capture-device", "CAPTURE", self._short_device(capture_device), GREEN),
            ("output-level", "OUTPUT LEVEL", f"{max(0, min(100, output_level))}%", YELLOW),
            ("power", "POWER OFF", "", RED),
        )
        maximum_offset = max(0, len(entries) - 4)
        offset = min(maximum_offset, max(0, offset))
        for row, (action, label, detail, accent) in enumerate(entries[offset : offset + 4]):
            top = 34 + row * 55
            rect = (8, top, 232, top + 49)
            draw.rectangle(rect, fill=DARK, outline=accent)
            if detail:
                self._text(draw, label, (14, top + 8), size=9)
                self._right_text(draw, detail, 224, top + 29, size=7, fill=DIM)
            else:
                self._center_text_in_rect(draw, label, rect, size=10)
            targets.append(HitTarget(action, rect))

        self._center_text(draw, f"IP {ip_address}", 257, size=7, fill=CYAN)

        back_rect = (0, 276, 80, 320)
        up_rect = (80, 276, 160, 320)
        down_rect = (160, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(draw, up_rect, "UP", accent=YELLOW, squared=True)
        self._button(draw, down_rect, "DOWN", accent=YELLOW, squared=True)
        targets.extend(
            (
                HitTarget("back", back_rect),
                HitTarget("settings-up", up_rect),
                HitTarget("settings-down", down_rect),
            )
        )
        return RenderedScreen(image, tuple(targets))

    def render_output_level(self, level: int) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        level = max(0, min(100, int(level)))
        self._header(draw, "OUTPUT LEVEL", "MUTED" if level == 0 else f"{level}%")

        self._center_text(draw, "DIGITAL TAPE SIGNAL", 58, size=8, fill=DIM)
        self._center_text(draw, "MUTED" if level == 0 else f"{level}%", 92, size=28, fill=YELLOW)
        bar_left, bar_top, bar_right, bar_bottom = 20, 142, 220, 156
        draw.rectangle((bar_left, bar_top, bar_right, bar_bottom), outline=DIM)
        fill_right = bar_left + int((bar_right - bar_left) * level / 100)
        if fill_right > bar_left:
            draw.rectangle((bar_left + 1, bar_top + 1, fill_right, bar_bottom - 1), fill=YELLOW)

        down_rect = (0, 190, 80, 258)
        mute_rect = (80, 190, 160, 258)
        up_rect = (160, 190, 240, 258)
        self._button(draw, down_rect, "-", accent=YELLOW, squared=True)
        self._button(draw, mute_rect, "MUTE", active=level == 0, accent=RED, squared=True)
        self._button(draw, up_rect, "+", accent=YELLOW, squared=True)
        targets.extend(
            (
                HitTarget("volume-down", down_rect),
                HitTarget("volume-mute", mute_rect),
                HitTarget("volume-up", up_rect),
            )
        )

        back_rect = (0, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        targets.append(HitTarget("back", back_rect))
        return RenderedScreen(image, tuple(targets))

    def render_audio_devices(
        self,
        title: str,
        devices: Sequence[tuple[str, str]],
        *,
        selected_device: str,
        offset: int = 0,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, title, f"{len(devices)}")

        if not devices:
            self._center_text(draw, "NO AUDIO DEVICES", 125, size=12, fill=RED)
            self._center_text(draw, "CONNECT USB AND TRY AGAIN", 158, size=8)
        for row, (name, alsa_name) in enumerate(devices[offset : offset + 5]):
            absolute_index = offset + row
            top = 34 + row * 45
            rect = (8, top, 232, top + 40)
            active = alsa_name == selected_device
            draw.rectangle(
                rect,
                fill=(30, 60, 65) if active else DARK,
                outline=GREEN if active else CYAN,
            )
            self._text(draw, name[:27], (14, top + 7), size=8)
            self._text(
                draw,
                self._short_device(alsa_name),
                (14, top + 23),
                size=7,
                fill=GREEN if active else DIM,
            )
            targets.append(HitTarget(f"select-audio:{absolute_index}", rect))

        back_rect = (0, 276, 80, 320)
        up_rect = (80, 276, 160, 320)
        down_rect = (160, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(draw, up_rect, "UP", accent=YELLOW, squared=True)
        self._button(draw, down_rect, "DOWN", accent=YELLOW, squared=True)
        targets.extend(
            (
                HitTarget("back", back_rect),
                HitTarget("audio-up", up_rect),
                HitTarget("audio-down", down_rect),
            )
        )
        return RenderedScreen(image, tuple(targets))

    def render_directories(
        self,
        current: Path,
        directories: Sequence[str],
        *,
        selected: int = 0,
        offset: int = 0,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "TAPE DIRECTORY", f"{len(directories)}")
        self._text(draw, self._short_path(current), (8, 32), size=8, fill=CYAN)

        visible = directories[offset : offset + 5]
        for index, name in enumerate(visible):
            absolute_index = offset + index
            top = 52 + index * 40
            rect = (8, top, 232, top + 35)
            if absolute_index == selected:
                draw.rectangle(rect, fill=(30, 60, 65), outline=CYAN)
            else:
                draw.rectangle(rect, outline=(55, 55, 55))
            self._text(draw, f"> {name[:22]}", (14, top + 10), size=10)
            targets.append(HitTarget(f"directory:{absolute_index}", rect))

        footer = (
            ("back", "BACK", 0, CYAN),
            ("parent", "PARENT", 48, YELLOW),
            ("directory-up", "UP", 96, YELLOW),
            ("directory-down", "DOWN", 144, YELLOW),
            ("use-directory", "USE", 192, GREEN),
        )
        for action, label, left, accent in footer:
            rect = (left, 276, left + 48, 320)
            self._button(draw, rect, label, accent=accent, squared=True)
            targets.append(HitTarget(action, rect))
        return RenderedScreen(image, tuple(targets))

    def render_power(self, *, requested: bool = False) -> RenderedScreen:
        image, draw = self._new_canvas()
        self._header(draw, "POWER", "SYSTEM")
        if requested:
            self._center_text(draw, "SHUTTING DOWN", 112, size=16, fill=RED)
            self._center_text(draw, "WAIT BEFORE REMOVING POWER", 155, size=8)
            return RenderedScreen(image)

        self._center_text(draw, "SHUT DOWN ZX DECK?", 85, size=12)
        self._center_text(draw, "WAIT FOR THE GREEN ACT LED", 125, size=8, fill=DIM)
        cancel_rect = (0, 270, 120, 320)
        power_rect = (120, 270, 240, 320)
        self._button(draw, cancel_rect, "CANCEL", accent=CYAN, squared=True)
        self._button(draw, power_rect, "POWER OFF", accent=RED, squared=True)
        return RenderedScreen(
            image,
            (
                HitTarget("cancel", cancel_rect),
                HitTarget("confirm-poweroff", power_rect),
            ),
        )

    def _new_canvas(self):
        try:
            from PIL import Image, ImageDraw
        except ImportError as exc:  # pragma: no cover - depends on host packages
            raise RuntimeError(
                "TouchRenderer requires Pillow. On Raspberry Pi OS install python3-pil."
            ) from exc
        image = Image.new("RGB", (WIDTH, HEIGHT), BLACK)
        return image, ImageDraw.Draw(image)

    def _font(self, size: int):
        from PIL import ImageFont

        font = self._fonts.get(size)
        if font is None:
            if self.font_path is not None and self.font_path.exists():
                font = ImageFont.truetype(str(self.font_path), size=size)
            else:
                try:
                    font = ImageFont.load_default(size=size)
                except TypeError:  # Pillow versions whose default has no size argument
                    font = ImageFont.load_default()
            self._fonts[size] = font
        return font

    @staticmethod
    def _short_path(path: Path, limit: int = 28) -> str:
        value = str(path)
        if len(value) <= limit:
            return value
        return "..." + value[-(limit - 3) :]

    @staticmethod
    def _short_device(value: str, limit: int = 29) -> str:
        return value if len(value) <= limit else "..." + value[-(limit - 3) :]

    def _header(self, draw, left: str, right: str) -> None:
        draw.rectangle((0, 0, WIDTH, 25), fill=(10, 10, 10))
        self._text(draw, left, (8, 7), size=10, fill=WHITE)
        self._right_text(draw, right, 232, 7, size=8, fill=CYAN)
        draw.line((0, 25, WIDTH, 25), fill=CYAN)

    def _button(
        self,
        draw,
        rect: tuple[int, int, int, int],
        label: str,
        *,
        active: bool = False,
        accent=CYAN,
        squared: bool = False,
    ) -> None:
        fill = accent if active else DARK
        text_fill = BLACK if active else WHITE
        if squared:
            draw.rectangle(rect, fill=fill, outline=accent)
        else:
            try:
                draw.rounded_rectangle(rect, radius=5, fill=fill, outline=accent, width=1)
            except AttributeError:  # pragma: no cover - old Pillow fallback
                draw.rectangle(rect, fill=fill, outline=accent)
        self._center_text_in_rect(draw, label, rect, size=10, fill=text_fill)

    def _text(self, draw, text: str, xy: tuple[int, int], *, size: int, fill=WHITE) -> None:
        draw.text(xy, text, font=self._font(size), fill=fill, spacing=0)

    def _right_text(self, draw, text: str, right: int, y: int, *, size: int, fill=WHITE) -> None:
        font = self._font(size)
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        draw.text((right - width, y), text, font=font, fill=fill)

    def _center_text(self, draw, text: str, y: int, *, size: int, fill=WHITE) -> None:
        font = self._font(size)
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        draw.text(((WIDTH - width) // 2, y), text, font=font, fill=fill)

    def _center_text_in_rect(
        self,
        draw,
        text: str,
        rect: tuple[int, int, int, int],
        *,
        size: int,
        y_offset: int = 0,
        fill=WHITE,
    ) -> None:
        font = self._font(size)
        box = draw.textbbox((0, 0), text, font=font)
        width = box[2] - box[0]
        height = box[3] - box[1]
        left, top, right, bottom = rect
        x = left + ((right - left) - width) // 2
        y = top + ((bottom - top) - height) // 2 - box[1] + y_offset
        draw.text((x, y), text, font=font, fill=fill)

    @staticmethod
    def _format_time(seconds: float | None) -> str:
        if seconds is None:
            return "--:--"
        total = max(0, int(seconds))
        minutes, secs = divmod(total, 60)
        if minutes < 100:
            return f"{minutes:02d}:{secs:02d}"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}:{minutes:02d}:{secs:02d}"


def marquee_offset(
    elapsed_seconds: float,
    maximum_offset: int,
    *,
    pixels_per_second: float = 30.0,
    start_hold_seconds: float = 1.5,
    end_hold_seconds: float = 1.0,
) -> int:
    """Return a smooth ping-pong title offset with readable pauses at both ends."""
    if maximum_offset <= 0 or pixels_per_second <= 0:
        return 0
    travel_seconds = maximum_offset / pixels_per_second
    cycle = start_hold_seconds + travel_seconds + end_hold_seconds + travel_seconds
    phase = max(0.0, elapsed_seconds) % cycle
    if phase < start_hold_seconds:
        return 0
    phase -= start_hold_seconds
    if phase < travel_seconds:
        return min(maximum_offset, int(phase * pixels_per_second))
    phase -= travel_seconds
    if phase < end_hold_seconds:
        return maximum_offset
    phase -= end_hold_seconds
    return max(0, maximum_offset - int(phase * pixels_per_second))
