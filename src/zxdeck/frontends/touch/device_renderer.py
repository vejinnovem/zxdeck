"""Device-facing touch renderer with operating-system status screens."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time

from zxdeck.system import primary_ipv4_address

from .renderer import (
    CYAN,
    DARK,
    DIM,
    GREEN,
    RED,
    YELLOW,
    HitTarget,
    RenderedScreen,
    TouchRenderer as BaseTouchRenderer,
)


class DeviceTouchRenderer(BaseTouchRenderer):
    """Add device status and administration screens to the base renderer."""

    def __init__(
        self,
        *,
        font_path: str | Path | None = None,
        address_provider: Callable[[], str | None] = primary_ipv4_address,
    ) -> None:
        super().__init__(font_path=font_path)
        self._address_provider = address_provider
        self._cached_address = "NO NETWORK"
        self._address_checked_at = float("-inf")

    def _network_address(self) -> str:
        now = time.monotonic()
        if now - self._address_checked_at >= 5.0:
            self._cached_address = self._address_provider() or "NO NETWORK"
            self._address_checked_at = now
        return self._cached_address

    def render_settings(
        self,
        *,
        playback_device: str = "default",
        capture_device: str = "default",
        output_level: int = 25,
        offset: int = 0,
        ip_address: str | None = None,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "SETTINGS", "DEVICE")

        entries = (
            ("directories", "TAPE DIRECTORY", "", CYAN),
            (
                "playback-device",
                "PLAYBACK",
                self._short_device(playback_device),
                GREEN,
            ),
            (
                "capture-device",
                "CAPTURE",
                self._short_device(capture_device),
                GREEN,
            ),
            (
                "output-level",
                "OUTPUT LEVEL",
                f"{max(0, min(100, output_level))}%",
                YELLOW,
            ),
            ("updates", "SOFTWARE UPDATE", "", CYAN),
            ("power", "POWER OFF", "", RED),
        )
        maximum_offset = max(0, len(entries) - 4)
        offset = min(maximum_offset, max(0, offset))

        for row, (action, label, detail, accent) in enumerate(
            entries[offset : offset + 4]
        ):
            top = 34 + row * 55
            rect = (8, top, 232, top + 49)
            draw.rectangle(rect, fill=DARK, outline=accent)
            if detail:
                self._text(draw, label, (14, top + 8), size=9)
                self._right_text(
                    draw,
                    detail,
                    224,
                    top + 29,
                    size=7,
                    fill=DIM,
                )
            else:
                self._center_text_in_rect(draw, label, rect, size=10)
            targets.append(HitTarget(action, rect))

        address = ip_address or self._network_address()
        self._center_text(draw, f"IP {address}", 257, size=7, fill=CYAN)

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

    def render_updates(
        self,
        *,
        installed_version: str = "--------",
        available_version: str = "--------",
        status: str = "NOT CHECKED",
        can_install: bool = False,
        busy: bool = False,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "SOFTWARE UPDATE", "GIT")

        self._text(draw, "INSTALLED", (12, 42), size=8, fill=DIM)
        self._right_text(
            draw,
            installed_version[:12] or "--------",
            228,
            42,
            size=10,
            fill=CYAN,
        )
        self._text(draw, "AVAILABLE", (12, 74), size=8, fill=DIM)
        self._right_text(
            draw,
            available_version[:12] or "--------",
            228,
            74,
            size=10,
            fill=GREEN if can_install else CYAN,
        )

        status_rect = (12, 112, 228, 222)
        status_upper = (status or "UNKNOWN").upper()
        status_color = YELLOW
        if "FAILED" in status_upper or "BLOCKED" in status_upper:
            status_color = RED
        elif "AVAILABLE" in status_upper or "INSTALLED" in status_upper:
            status_color = GREEN
        draw.rectangle(status_rect, fill=DARK, outline=status_color)

        words = status_upper.split()
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = word if not line else f"{line} {word}"
            if len(candidate) <= 24:
                line = candidate
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
        if not lines:
            lines = ["UNKNOWN"]
        lines = lines[:3]
        start_y = 140 - (len(lines) - 1) * 10
        for index, value in enumerate(lines):
            self._center_text(
                draw,
                value[:28],
                start_y + index * 21,
                size=10,
                fill=status_color,
            )

        if busy:
            self._center_text(draw, "PLEASE WAIT", 195, size=8, fill=DIM)

        back_rect = (0, 276, 80, 320)
        check_rect = (80, 276, 160, 320)
        update_rect = (160, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(
            draw,
            check_rect,
            "WAIT" if busy else "CHECK",
            accent=YELLOW,
            squared=True,
        )
        self._button(
            draw,
            update_rect,
            "UPDATE",
            accent=GREEN if can_install else DIM,
            squared=True,
        )
        targets.append(HitTarget("back", back_rect))
        if not busy:
            targets.append(HitTarget("check-update", check_rect))
            if can_install:
                targets.append(HitTarget("install-update", update_rect))
        return RenderedScreen(image, tuple(targets))


TouchRenderer = DeviceTouchRenderer
