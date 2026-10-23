"""Hardware-independent controller for the interactive touch UI prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from zxdeck.core.state import DeckState, TransportState

from .keypad import MultiTapEditor
from .renderer import RenderedScreen, Screen, TouchRenderer


@dataclass(slots=True)
class TouchUIController:
    """Own navigation and mock actions while the real services do not exist.

    This controller deliberately does not access GPIO, SPI, storage or audio.
    It can therefore be exercised on a development machine and replaced by
    backend commands as the tape services are implemented.
    """

    files: Sequence[str]
    state: DeckState = field(default_factory=DeckState)
    screen: Screen = Screen.HOME
    selected_file: int = 0
    file_offset: int = 0
    editor: MultiTapEditor = field(default_factory=MultiTapEditor)
    visible_file_count: int = 6

    def render(self, renderer: TouchRenderer) -> RenderedScreen:
        if self.screen is Screen.HOME:
            return renderer.render_home(self.state)
        if self.screen is Screen.FILES:
            return renderer.render_files(
                self.files,
                selected=self.selected_file,
                offset=self.file_offset,
            )
        if self.screen is Screen.FILENAME:
            return renderer.render_filename(self.editor)
        return renderer.render_settings()

    def handle_action(self, action: str) -> None:
        if self.screen is Screen.HOME:
            self._handle_home(action)
        elif self.screen is Screen.FILES:
            self._handle_files(action)
        elif self.screen is Screen.FILENAME:
            self._handle_filename(action)
        elif self.screen is Screen.SETTINGS and action == "back":
            self.screen = Screen.HOME

    def _handle_home(self, action: str) -> None:
        if action == "files":
            self.screen = Screen.FILES
        elif action == "new":
            self.editor = MultiTapEditor()
            self.screen = Screen.FILENAME
        elif action == "settings":
            self.screen = Screen.SETTINGS
        elif action == "play":
            self.state = self.state.next_revision(transport=TransportState.PLAYING)
        elif action == "stop":
            self.state = self.state.next_revision(transport=TransportState.STOPPED)
        elif action == "record":
            self.state = self.state.next_revision(transport=TransportState.RECORDING)
        elif action == "rewind":
            self.state = self.state.next_revision(position_seconds=0.0)

    def _handle_files(self, action: str) -> None:
        if action == "back":
            self.screen = Screen.HOME
            return
        if action == "up":
            self.selected_file = max(0, self.selected_file - 1)
            self._ensure_selection_visible()
            return
        if action == "down":
            if self.files:
                self.selected_file = min(len(self.files) - 1, self.selected_file + 1)
                self._ensure_selection_visible()
            return
        if action == "open-selected":
            self._open_file(self.selected_file)
            return
        if action.startswith("open:"):
            try:
                index = int(action.split(":", 1)[1])
            except ValueError:
                return
            self._open_file(index)

    def _handle_filename(self, action: str) -> None:
        if action == "cancel":
            self.screen = Screen.HOME
        elif action == "save":
            name = self.editor.text.strip() or "UNTITLED"
            if "." not in Path(name).name:
                name += ".TZX"
            self.state = self.state.next_revision(tape_name=name)
            self.screen = Screen.HOME
        elif action.startswith("key:"):
            self.editor.press(action.split(":", 1)[1])

    def _open_file(self, index: int) -> None:
        if not 0 <= index < len(self.files):
            return
        self.selected_file = index
        self._ensure_selection_visible()
        self.state = self.state.next_revision(tape_name=self.files[index])
        self.screen = Screen.HOME

    def _ensure_selection_visible(self) -> None:
        if self.selected_file < self.file_offset:
            self.file_offset = self.selected_file
        elif self.selected_file >= self.file_offset + self.visible_file_count:
            self.file_offset = self.selected_file - self.visible_file_count + 1
