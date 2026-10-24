"""Device-facing touch renderer with operating-system status screens."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time

from zxdeck.audio import HardwareOutputState, hardware_output_state
from zxdeck.system import WifiNetwork, connected_wifi_ssid, primary_ipv4_address

from .keypad import MultiTapEditor
from .renderer import (
    CYAN,
    DARK,
    DIM,
    GREEN,
    RED,
    WHITE,
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
        wifi_provider: Callable[[], str | None] = connected_wifi_ssid,
        hardware_output_provider: Callable[
            [str], HardwareOutputState | None
        ] = hardware_output_state,
    ) -> None:
        super().__init__(font_path=font_path)
        self._address_provider = address_provider
        self._wifi_provider = wifi_provider
        self._hardware_output_provider = hardware_output_provider
        self._cached_address = "NO NETWORK"
        self._address_checked_at = float("-inf")
        self._cached_wifi = "DISCONNECTED"
        self._wifi_checked_at = float("-inf")
        self._cached_hardware_device = ""
        self._cached_hardware_output: HardwareOutputState | None = None
        self._hardware_checked_at = float("-inf")

    def _network_address(self) -> str:
        now = time.monotonic()
        if now - self._address_checked_at >= 5.0:
            self._cached_address = self._address_provider() or "NO NETWORK"
            self._address_checked_at = now
        return self._cached_address

    def _wifi_ssid(self) -> str:
        now = time.monotonic()
        if now - self._wifi_checked_at >= 5.0:
            self._cached_wifi = self._wifi_provider() or "DISCONNECTED"
            self._wifi_checked_at = now
        return self._cached_wifi

    def invalidate_network_status(self) -> None:
        self._address_checked_at = float("-inf")
        self._wifi_checked_at = float("-inf")

    def _hardware_output(self, playback_device: str) -> HardwareOutputState | None:
        return self._hardware_output_provider(playback_device)

    def invalidate_hardware_output(self) -> None:
        self._hardware_checked_at = float("-inf")

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

        hardware = self._hardware_output(playback_device)
        hardware_detail = "N/A" if hardware is None else f"{hardware.level}%"
        wifi_detail = self._wifi_ssid()

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
                "TAPE SIGNAL",
                f"{max(0, min(100, output_level))}%",
                YELLOW,
            ),
            (
                "hardware-output",
                "CARD OUTPUT",
                hardware_detail,
                YELLOW,
            ),
            ("wifi", "WI-FI", wifi_detail[:20], GREEN),
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

    def render_hardware_output_level(
        self,
        playback_device: str,
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        state = self._hardware_output(playback_device)
        if state is None:
            self._header(draw, "CARD OUTPUT", "N/A")
            self._center_text(draw, "NO PLAYBACK MIXER", 100, size=13, fill=RED)
            self._center_text(
                draw,
                "TRY ANOTHER PLAYBACK DEVICE",
                136,
                size=8,
                fill=DIM,
            )
        else:
            level = max(0, min(100, state.level))
            self._header(
                draw,
                "CARD OUTPUT",
                "MUTED" if level == 0 else f"{level}%",
            )
            self._center_text(
                draw,
                state.control_name[:24],
                54,
                size=8,
                fill=DIM,
            )
            self._center_text(
                draw,
                "MUTED" if level == 0 else f"{level}%",
                92,
                size=28,
                fill=YELLOW,
            )
            bar_left, bar_top, bar_right, bar_bottom = 20, 142, 220, 156
            draw.rectangle(
                (bar_left, bar_top, bar_right, bar_bottom),
                outline=DIM,
            )
            fill_right = bar_left + int(
                (bar_right - bar_left) * level / 100
            )
            if fill_right > bar_left:
                draw.rectangle(
                    (
                        bar_left + 1,
                        bar_top + 1,
                        fill_right,
                        bar_bottom - 1,
                    ),
                    fill=YELLOW,
                )

            down_rect = (0, 190, 80, 258)
            mute_rect = (80, 190, 160, 258)
            up_rect = (160, 190, 240, 258)
            self._button(
                draw,
                down_rect,
                "-",
                accent=YELLOW,
                squared=True,
            )
            self._button(
                draw,
                mute_rect,
                "MUTE",
                active=level == 0,
                accent=RED,
                squared=True,
            )
            self._button(
                draw,
                up_rect,
                "+",
                accent=YELLOW,
                squared=True,
            )
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

    def render_wifi_networks(
        self,
        networks: tuple[WifiNetwork, ...] | list[WifiNetwork],
        *,
        offset: int = 0,
        status: str = "",
    ) -> RenderedScreen:
        image, draw = self._new_canvas()
        targets: list[HitTarget] = []
        self._header(draw, "WI-FI", f"{len(networks)}")

        visible = networks[offset : offset + 5]
        if not visible:
            self._center_text(draw, "NO NETWORKS", 115, size=13, fill=RED)
            self._center_text(draw, "TAP SCAN", 146, size=9, fill=DIM)

        for row, network in enumerate(visible):
            absolute_index = offset + row
            top = 32 + row * 44
            rect = (6, top, 234, top + 39)
            active = network.active
            draw.rectangle(
                rect,
                fill=(30, 60, 65) if active else DARK,
                outline=GREEN if active else CYAN,
            )
            self._text(
                draw,
                network.ssid[:22],
                (12, top + 7),
                size=9,
                fill=WHITE,
            )
            security = "LOCK" if network.secured else "OPEN"
            detail = f"{network.signal}% {security}"
            self._right_text(
                draw,
                detail,
                228,
                top + 23,
                size=7,
                fill=GREEN if active else DIM,
            )
            targets.append(
                HitTarget(f"select-wifi:{absolute_index}", rect)
            )

        if status:
            self._center_text(
                draw,
                status.upper()[:32],
                257,
                size=7,
                fill=GREEN if "CONNECTED" in status.upper() else DIM,
            )

        back_rect = (0, 276, 60, 320)
        up_rect = (60, 276, 120, 320)
        down_rect = (120, 276, 180, 320)
        scan_rect = (180, 276, 240, 320)
        self._button(draw, back_rect, "BACK", accent=CYAN, squared=True)
        self._button(draw, up_rect, "UP", accent=YELLOW, squared=True)
        self._button(draw, down_rect, "DOWN", accent=YELLOW, squared=True)
        self._button(draw, scan_rect, "SCAN", accent=GREEN, squared=True)
        targets.extend(
            (
                HitTarget("back", back_rect),
                HitTarget("wifi-up", up_rect),
                HitTarget("wifi-down", down_rect),
                HitTarget("wifi-rescan", scan_rect),
            )
        )
        return RenderedScreen(image, tuple(targets))

    def render_wifi_password(
        self,
        editor: MultiTapEditor,
        ssid: str,
        *,
        cursor_visible: bool = True,
    ) -> RenderedScreen:
        masked = MultiTapEditor(
            text="*" * len(editor.text),
            mode=editor.mode,
            timeout_seconds=editor.timeout_seconds,
            max_length=editor.max_length,
        )
        title = f"WIFI {ssid[:13]}" if ssid else "WIFI PASSWORD"
        return self.render_filename(
            masked,
            cursor_visible=cursor_visible and not editor.has_pending_character,
            title=title,
            accept_label="CONNECT",
            accept_action="wifi-connect",
        )

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
