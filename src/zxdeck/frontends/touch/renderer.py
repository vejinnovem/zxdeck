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
    SETTINGS = "settings"


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

    def render_home(self, state: DeckState) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []

        self._header(draw, "ZX DECK", state.transport.value.upper())

        tape_name = state.tape_name or "NO TAPE"
        self._center_text(draw, tape_name[:24], 47, size=16)

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

    def render_files(
        self,
        files: Sequence[str],
        *,
        selected: int = 0,
        offset: int = 0,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "FILES", f"{len(files)}")

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
        select_rect = (180, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(draw, up_rect, "UP", accent=YELLOW, squared=True)
        self._button(draw, down_rect, "DOWN", accent=YELLOW, squared=True)
        self._button(draw, select_rect, "OPEN", accent=GREEN, squared=True)
        targets.extend(
            (
                HitTarget("back", back_rect),
                HitTarget("up", up_rect),
                HitTarget("down", down_rect),
                HitTarget("open-selected", select_rect),
            )
        )
        return RenderedScreen(image, tuple(targets))

    def render_filename(self, editor: MultiTapEditor) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "SAVE AS", editor.mode.value)

        draw.rectangle((8, 32, 232, 67), outline=CYAN)
        value = editor.text[-25:] + "_"
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

        cancel_rect = (0, 270, 120, 320)
        save_rect = (120, 270, 240, 320)
        self._button(draw, cancel_rect, "CANCEL", accent=RED, squared=True)
        self._button(draw, save_rect, "SAVE", accent=GREEN, squared=True)
        targets.extend((HitTarget("cancel", cancel_rect), HitTarget("save", save_rect)))
        return RenderedScreen(image, tuple(targets))

    def render_settings(self) -> RenderedScreen:
        image, draw = self._new_canvas()
        self._header(draw, "SETTINGS", "DEVICE")
        self._center_text(draw, "DISPLAY SETTINGS", 75, size=12)
        self._center_text(draw, "WEB OPTIONS LIVE IN WEB UI", 118, size=8, fill=DIM)
        back_rect = (0, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        return RenderedScreen(image, (HitTarget("back", back_rect),))

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

        if self.font_path is not None and self.font_path.exists():
            return ImageFont.truetype(str(self.font_path), size=size)
        try:
            return ImageFont.load_default(size=size)
        except TypeError:  # Pillow versions whose default font has no size argument
            return ImageFont.load_default()

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
