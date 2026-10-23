"""Hardware-independent controller for the interactive touch UI prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from zxdeck.core.state import DeckState, TransportState
from zxdeck.storage import DirectoryBrowser, DirectoryUnavailable

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
    search_query: str = ""
    directory_browser: DirectoryBrowser | None = None
    selected_storage_path: Path | None = None
    shutdown_requested: bool = False
    directory_selected: int = 0
    directory_offset: int = 0
    visible_directory_count: int = 5

    def render(
        self,
        renderer: TouchRenderer,
        *,
        cursor_visible: bool = True,
    ) -> RenderedScreen:
        if self.screen is Screen.HOME:
            return renderer.render_home(self.state)
        if self.screen is Screen.FILES:
            files = self.filtered_files
            return renderer.render_files(
                files,
                selected=self.selected_file,
                offset=self.file_offset,
                query=self.search_query,
            )
        if self.screen is Screen.FILENAME:
            return renderer.render_filename(
                self.editor,
                cursor_visible=cursor_visible,
            )
        if self.screen is Screen.SEARCH:
            return renderer.render_search(
                self.editor,
                cursor_visible=cursor_visible,
            )
        if self.screen is Screen.SETTINGS:
            return renderer.render_settings()
        if self.screen is Screen.DIRECTORIES and self.directory_browser is not None:
            return renderer.render_directories(
                self.directory_browser.current,
                self.directory_browser.directories(),
                selected=self.directory_selected,
                offset=self.directory_offset,
            )
        return renderer.render_power(requested=self.shutdown_requested)

    @property
    def filtered_files(self) -> tuple[str, ...]:
        needle = self.search_query.casefold().strip()
        if not needle:
            return tuple(self.files)
        return tuple(name for name in self.files if needle in name.casefold())

    def handle_action(self, action: str) -> None:
        if self.screen is Screen.HOME:
            self._handle_home(action)
        elif self.screen is Screen.FILES:
            self._handle_files(action)
        elif self.screen is Screen.FILENAME:
            self._handle_filename(action)
        elif self.screen is Screen.SEARCH:
            self._handle_search(action)
        elif self.screen is Screen.SETTINGS:
            self._handle_settings(action)
        elif self.screen is Screen.DIRECTORIES:
            self._handle_directories(action)
        elif self.screen is Screen.POWER:
            self._handle_power(action)

    def _handle_home(self, action: str) -> None:
        if action == "files":
            self.screen = Screen.FILES
        elif action == "new":
            self._stop_transport()
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
        if action == "search":
            self.editor = MultiTapEditor(text=self.search_query)
            self.screen = Screen.SEARCH
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
            self.state = self.state.next_revision(
                tape_name=name,
                transport=TransportState.STOPPED,
            )
            self.screen = Screen.HOME
        elif action.startswith("key:"):
            self.editor.press(action.split(":", 1)[1])

    def _handle_search(self, action: str) -> None:
        if action == "cancel":
            self.screen = Screen.FILES
        elif action == "apply-search":
            self.search_query = self.editor.text.strip()
            self.selected_file = 0
            self.file_offset = 0
            self.screen = Screen.FILES
        elif action.startswith("key:"):
            self.editor.press(action.split(":", 1)[1])

    def _handle_settings(self, action: str) -> None:
        if action == "back":
            self.screen = Screen.HOME
        elif action == "power":
            self.screen = Screen.POWER
        elif action == "directories" and self.directory_browser is not None:
            self.directory_selected = 0
            self.directory_offset = 0
            self.screen = Screen.DIRECTORIES

    def _handle_directories(self, action: str) -> None:
        browser = self.directory_browser
        if browser is None:
            self.screen = Screen.SETTINGS
            return
        directories = browser.directories()
        if action == "back":
            self.screen = Screen.SETTINGS
        elif action == "parent":
            browser.parent()
            self.directory_selected = 0
            self.directory_offset = 0
        elif action == "directory-up":
            self.directory_selected = max(0, self.directory_selected - 1)
            self._ensure_directory_visible()
        elif action == "directory-down" and directories:
            self.directory_selected = min(
                len(directories) - 1,
                self.directory_selected + 1,
            )
            self._ensure_directory_visible()
        elif action == "use-directory":
            self.selected_storage_path = browser.current
            self.screen = Screen.SETTINGS
        elif action.startswith("directory:"):
            try:
                index = int(action.split(":", 1)[1])
                browser.enter(directories[index])
            except (ValueError, IndexError, DirectoryUnavailable):
                return
            self.directory_selected = 0
            self.directory_offset = 0

    def _handle_power(self, action: str) -> None:
        if action == "cancel":
            self.screen = Screen.SETTINGS
        elif action == "confirm-poweroff":
            self._stop_transport()
            self.shutdown_requested = True

    def _open_file(self, index: int) -> None:
        if not 0 <= index < len(self.files):
            return
        self.selected_file = index
        self._ensure_selection_visible()
        files = self.filtered_files
        if not 0 <= index < len(files):
            return
        self.state = self.state.next_revision(
            tape_name=files[index],
            transport=TransportState.STOPPED,
        )
        self.screen = Screen.HOME

    def _ensure_selection_visible(self) -> None:
        if self.selected_file < self.file_offset:
            self.file_offset = self.selected_file
        elif self.selected_file >= self.file_offset + self.visible_file_count:
            self.file_offset = self.selected_file - self.visible_file_count + 1

    def _ensure_directory_visible(self) -> None:
        if self.directory_selected < self.directory_offset:
            self.directory_offset = self.directory_selected
        elif (
            self.directory_selected
            >= self.directory_offset + self.visible_directory_count
        ):
            self.directory_offset = (
                self.directory_selected - self.visible_directory_count + 1
            )

    def _stop_transport(self) -> None:
        if self.state.transport is not TransportState.STOPPED:
            self.state = self.state.next_revision(transport=TransportState.STOPPED)
