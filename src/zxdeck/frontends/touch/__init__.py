"""Local 240x320 touchscreen frontend for ZX Deck.

The base renderer/controller stay hardware-independent. Device variants add
operating-system status and controls used on the Raspberry Pi appliance.
"""

from __future__ import annotations

import time

from .controller import TouchUIController as BaseTouchUIController
from .device_controller import DeviceTouchUIController
from .keypad import InputMode, MultiTapEditor
from .renderer import Screen, TouchRenderer
from .runtime_renderer import DeviceTouchRenderer as RuntimeDeviceTouchRenderer


class DeviceTouchRenderer(RuntimeDeviceTouchRenderer):
    """Runtime renderer with a short cache for expensive settings-only reads."""

    SETTINGS_HARDWARE_CACHE_SECONDS = 2.0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._settings_render_active = False

    def render_settings(self, *args, **kwargs):
        self._settings_render_active = True
        try:
            return super().render_settings(*args, **kwargs)
        finally:
            self._settings_render_active = False

    def _hardware_output(self, playback_device: str):
        # The dedicated CARD OUTPUT screen must always reflect button presses
        # immediately.  Only SETTINGS uses the cache, where spawning amixer on
        # every UP/DOWN redraw is unnecessary and noticeably stalls a Pi Zero.
        if not self._settings_render_active:
            return self._hardware_output_provider(playback_device)

        now = time.monotonic()
        if (
            playback_device != self._cached_hardware_device
            or now - self._hardware_checked_at >= self.SETTINGS_HARDWARE_CACHE_SECONDS
        ):
            self._cached_hardware_device = playback_device
            self._cached_hardware_output = self._hardware_output_provider(
                playback_device
            )
            self._hardware_checked_at = now
        return self._cached_hardware_output


class TouchUIController(DeviceTouchUIController):
    """Device controller with page-wise navigation for compact touch lists."""

    def _handle_files(self, action: str) -> None:
        if action not in {"up", "down"}:
            super()._handle_files(action)
            return

        files = self.filtered_files
        if not files:
            return

        direction = -1 if action == "up" else 1
        if len(files) <= self.visible_file_count:
            # If everything already fits on one screen there is no page to
            # scroll, so keep ordinary selection movement useful.
            self.selected_file = min(
                len(files) - 1,
                max(0, self.selected_file + direction),
            )
            self._ensure_selection_visible()
            return

        step = self.visible_file_count
        maximum_offset = max(0, len(files) - step)
        self.selected_file = min(
            len(files) - 1,
            max(0, self.selected_file + direction * step),
        )
        self.file_offset = min(
            maximum_offset,
            max(0, self.file_offset + direction * step),
        )
        self._ensure_selection_visible()

    def _handle_settings(self, action: str) -> None:
        if action in {"settings-up", "settings-down"}:
            direction = -1 if action == "settings-up" else 1
            step = self.visible_settings_count
            maximum_offset = max(
                0,
                self.settings_entry_count - self.visible_settings_count,
            )
            self.settings_offset = min(
                maximum_offset,
                max(0, self.settings_offset + direction * step),
            )
            return
        super()._handle_settings(action)


__all__ = [
    "BaseTouchUIController",
    "DeviceTouchRenderer",
    "DeviceTouchUIController",
    "InputMode",
    "MultiTapEditor",
    "Screen",
    "TouchRenderer",
    "TouchUIController",
]
