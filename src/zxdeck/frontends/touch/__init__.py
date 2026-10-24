"""Local 240x320 touchscreen frontend for ZX Deck.

The base renderer/controller stay hardware-independent. Device variants add
operating-system status and controls used on the Raspberry Pi appliance.
"""

from __future__ import annotations

import time

from zxdeck.core.state import TransportState
from zxdeck.tape import TapeDecodeError, inspect_tape_timeline, select_tape_segment

from .controller import TouchUIController as BaseTouchUIController
from .device_controller import DeviceTouchUIController
from .keypad import InputMode, MultiTapEditor
from .renderer import (
    BLACK,
    CYAN,
    DIM,
    RED,
    WHITE,
    HitTarget,
    Screen,
    TouchRenderer,
)
from .runtime_renderer import DeviceTouchRenderer as RuntimeDeviceTouchRenderer


class DeviceTouchRenderer(RuntimeDeviceTouchRenderer):
    """Runtime renderer with cached settings reads and segment transport UI."""

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

    def _draw_segment_markers(self, image, state) -> None:
        """Draw compact boundary ticks without competing with the playhead."""
        duration = state.duration_seconds
        starts = state.segment_starts
        if not starts or duration is None or duration <= 0:
            return

        from PIL import ImageDraw

        draw = ImageDraw.Draw(image)
        left, right = 17, 223
        width = right - left
        for index, start in enumerate(starts):
            ratio = min(1.0, max(0.0, start / duration))
            x = left + round(width * ratio)
            colour = WHITE if index + 1 == state.segment_index else DIM
            draw.line((x, 78, x, 81), fill=colour)
            draw.line((x, 93, x, 96), fill=colour)

    def decorate_signal_progress(
        self,
        image,
        state,
        *,
        phase: str | None,
        animation_step: int = 0,
    ) -> None:
        # Runtime stripes repaint the progress-bar pixels, so restore the
        # segment ticks afterwards from the same state used by navigation.
        super().decorate_signal_progress(
            image,
            state,
            phase=phase,
            animation_step=animation_step,
        )
        self._draw_segment_markers(image, state)

    def render_home(self, state):
        """Replace the original transport row with segment navigation."""
        rendered = super().render_home(state)

        from PIL import ImageDraw

        draw = ImageDraw.Draw(rendered.image)
        self._draw_segment_markers(rendered.image, state)
        draw.rectangle((0, 112, 240, 235), fill=BLACK)

        if state.segment_count:
            label = f"{state.segment_index}/{state.segment_count} {state.segment_label or 'SEGMENT'}"
            fitted = self._fit_text_to_width(
                draw,
                label,
                max_width=220,
                size=7,
            )
            self._center_text(draw, fitted, 112, size=7, fill=DIM)

        first_row = (
            ("rewind", "<<", (16, 128, 74, 174)),
            ("play", "PLAY", (91, 128, 149, 174)),
            ("forward", ">>", (166, 128, 224, 174)),
        )
        second_row = (
            ("stop", "STOP", (16, 185, 112, 229), CYAN),
            ("record", "REC", (128, 185, 224, 229), RED),
        )

        targets = [
            target
            for target in rendered.targets
            if target.action not in {"rewind", "play", "forward", "stop", "record"}
        ]
        for action, label, rect in first_row:
            active = action == "play" and state.transport is TransportState.PLAYING
            self._button(draw, rect, label, active=active, accent=CYAN)
            targets.append(HitTarget(action, rect))
        for action, label, rect, accent in second_row:
            active = (
                (action == "stop" and state.transport is TransportState.STOPPED)
                or (action == "record" and state.transport is TransportState.RECORDING)
            )
            self._button(draw, rect, label, active=active, accent=accent)
            targets.append(HitTarget(action, rect))

        return type(rendered)(rendered.image, tuple(targets))


class TouchUIController(DeviceTouchUIController):
    """Device controller with page navigation and tape-segment transport."""

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

    @property
    def tape_segments(self):
        return getattr(self, "_tape_segments", ())

    def _open_file(self, index: int) -> None:
        super()._open_file(index)
        if self.screen is Screen.HOME:
            self._load_segment_navigation()

    def _handle_saves(self, action: str) -> None:
        super()._handle_saves(action)
        if self.screen is Screen.HOME and action.startswith("open-save:"):
            self._load_segment_navigation()

    def _load_segment_navigation(self) -> None:
        path = self.selected_tape_path
        segments = ()
        duration_seconds = None
        if path is not None:
            try:
                timeline = inspect_tape_timeline(path)
                segments = timeline.segments
                duration_seconds = timeline.duration_seconds
            except (OSError, TapeDecodeError, ValueError):
                segments = ()
        self._tape_segments = segments
        self._tape_duration_seconds = duration_seconds
        if not segments:
            self.state = self.state.next_revision(
                duration_seconds=duration_seconds,
                segment_label=None,
                segment_index=0,
                segment_count=0,
                segment_starts=(),
            )
            return
        self._select_segment(0)

    def _segment_index_for_position(self, position: float) -> int:
        segments = self.tape_segments
        if not segments:
            return 0
        selected = 0
        for index, segment in enumerate(segments):
            if segment.start_seconds <= position + 1e-6:
                selected = index
            else:
                break
        return selected

    def _select_segment(self, index: int) -> None:
        segments = self.tape_segments
        path = self.selected_tape_path
        if not segments or path is None:
            return
        index = min(len(segments) - 1, max(0, int(index)))
        segment = segments[index]
        self._selected_segment = index
        select_tape_segment(path, segment.event_index)
        self.state = self.state.next_revision(
            transport=TransportState.STOPPED,
            position_seconds=segment.start_seconds,
            duration_seconds=getattr(self, "_tape_duration_seconds", None),
            error=None,
            segment_label=segment.label,
            segment_index=index + 1,
            segment_count=len(segments),
            segment_starts=tuple(item.start_seconds for item in segments),
        )

    def _sync_segment_metadata(self) -> None:
        segments = self.tape_segments
        if not segments:
            return
        index = self._segment_index_for_position(self.state.position_seconds)
        segment = segments[index]
        self._selected_segment = index
        if (
            self.state.segment_index != index + 1
            or self.state.segment_label != segment.label
            or self.state.segment_count != len(segments)
        ):
            self.state = self.state.next_revision(
                segment_label=segment.label,
                segment_index=index + 1,
                segment_count=len(segments),
            )

    def render(self, renderer, *, cursor_visible: bool = True):
        if self.screen is Screen.HOME:
            self._sync_segment_metadata()
        return super().render(renderer, cursor_visible=cursor_visible)

    def _handle_home(self, action: str) -> None:
        if action == "new":
            self._tape_segments = ()
            self._selected_segment = 0
            self._tape_duration_seconds = None
            self.state = self.state.next_revision(
                segment_label=None,
                segment_index=0,
                segment_count=0,
                segment_starts=(),
            )
            super()._handle_home(action)
            return

        if action in {"rewind", "forward"} and self.tape_segments:
            current = self._segment_index_for_position(self.state.position_seconds)
            direction = -1 if action == "rewind" else 1
            target = min(
                len(self.tape_segments) - 1,
                max(0, current + direction),
            )
            if target != current:
                self._select_segment(target)
            elif self.state.transport is TransportState.PLAYING:
                # A transport navigation press always behaves like a physical
                # tape operation: stop before the user resumes with PLAY.
                self.state = self.state.next_revision(transport=TransportState.STOPPED)
            return

        if action == "play" and self.tape_segments and self.state.tape_name:
            index = self._segment_index_for_position(self.state.position_seconds)
            segment = self.tape_segments[index]
            path = self.selected_tape_path
            if path is not None:
                select_tape_segment(path, segment.event_index)
            self._selected_segment = index
            self.state = self.state.next_revision(
                transport=TransportState.PLAYING,
                position_seconds=segment.start_seconds,
                error=None,
                segment_label=segment.label,
                segment_index=index + 1,
                segment_count=len(self.tape_segments),
            )
            return

        if action == "forward":
            return
        super()._handle_home(action)


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
