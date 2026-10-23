"""Hardware-independent controller for the interactive touch UI prototype."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from zxdeck.audio import AudioDevice
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
    file_paths: Sequence[Path] | None = None
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
    playback_devices: Sequence[AudioDevice] = ()
    capture_devices: Sequence[AudioDevice] = ()
    selected_playback_device: str = "default"
    selected_capture_device: str = "default"
    audio_offset: int = 0
    visible_audio_count: int = 5

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
        if self.screen is Screen.LETTERS:
            return renderer.render_letters()
        if self.screen is Screen.SETTINGS:
            return renderer.render_settings(
                playback_device=self.selected_playback_device,
                capture_device=self.selected_capture_device,
            )
        if self.screen is Screen.DIRECTORIES and self.directory_browser is not None:
            return renderer.render_directories(
                self.directory_browser.current,
                self.directory_browser.directories(),
                selected=self.directory_selected,
                offset=self.directory_offset,
            )
        if self.screen in {Screen.AUDIO_PLAYBACK, Screen.AUDIO_CAPTURE}:
            devices = self._current_audio_devices()
            selected = (
                self.selected_playback_device
                if self.screen is Screen.AUDIO_PLAYBACK
                else self.selected_capture_device
            )
            title = "PLAYBACK DEVICE" if self.screen is Screen.AUDIO_PLAYBACK else "CAPTURE DEVICE"
            return renderer.render_audio_devices(
                title,
                tuple((device.name, device.alsa_name) for device in devices),
                selected_device=selected,
                offset=self.audio_offset,
            )
        return renderer.render_power(requested=self.shutdown_requested)

    @property
    def filtered_files(self) -> tuple[str, ...]:
        return tuple(self.files[index] for index in self.filtered_file_indices)

    @property
    def filtered_file_indices(self) -> tuple[int, ...]:
        needle = self.search_query.casefold().strip()
        if not needle:
            return tuple(range(len(self.files)))
        return tuple(
            index
            for index, name in enumerate(self.files)
            if needle in name.casefold()
        )

    @property
    def selected_tape_path(self) -> Path | None:
        if self.file_paths is None:
            return None
        indices = self.filtered_file_indices
        if not 0 <= self.selected_file < len(indices):
            return None
        return Path(self.file_paths[indices[self.selected_file]])

    def handle_action(self, action: str) -> None:
        if self.screen is Screen.HOME:
            self._handle_home(action)
        elif self.screen is Screen.FILES:
            self._handle_files(action)
        elif self.screen is Screen.FILENAME:
            self._handle_filename(action)
        elif self.screen is Screen.SEARCH:
            self._handle_search(action)
        elif self.screen is Screen.LETTERS:
            self._handle_letters(action)
        elif self.screen is Screen.SETTINGS:
            self._handle_settings(action)
        elif self.screen is Screen.DIRECTORIES:
            self._handle_directories(action)
        elif self.screen in {Screen.AUDIO_PLAYBACK, Screen.AUDIO_CAPTURE}:
            self._handle_audio_devices(action)
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
            if self.state.tape_name is None:
                self.state = self.state.next_revision(error="SELECT A TAPE")
            else:
                self.state = self.state.next_revision(
                    transport=TransportState.PLAYING,
                    error=None,
                )
        elif action == "stop":
            self.state = self.state.next_revision(transport=TransportState.STOPPED)
        elif action == "record":
            if self.state.tape_name is None:
                self.state = self.state.next_revision(error="NAME THE TAPE")
            else:
                self.state = self.state.next_revision(
                    transport=TransportState.RECORDING,
                    error=None,
                )
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
            files = self.filtered_files
            if files:
                self.selected_file = min(len(files) - 1, self.selected_file + 1)
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
        elif action == "letters":
            self.screen = Screen.LETTERS
        elif action.startswith("key:"):
            self.editor.press(action.split(":", 1)[1])

    def _handle_letters(self, action: str) -> None:
        if action == "back":
            self.screen = Screen.SEARCH
            return
        if not action.startswith("jump:"):
            return
        initial = action.split(":", 1)[1].upper()
        if initial not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ#":
            return
        self.search_query = ""
        for index, name in enumerate(self.files):
            first = name[:1].upper()
            group = first if "A" <= first <= "Z" else "#"
            if group == initial:
                self.selected_file = index
                self.file_offset = index
                self.screen = Screen.FILES
                return

    def _handle_settings(self, action: str) -> None:
        if action == "back":
            self.screen = Screen.HOME
        elif action == "power":
            self.screen = Screen.POWER
        elif action == "directories" and self.directory_browser is not None:
            self.directory_selected = 0
            self.directory_offset = 0
            self.screen = Screen.DIRECTORIES
        elif action == "playback-device":
            self.audio_offset = 0
            self.screen = Screen.AUDIO_PLAYBACK
        elif action == "capture-device":
            self.audio_offset = 0
            self.screen = Screen.AUDIO_CAPTURE

    def _handle_audio_devices(self, action: str) -> None:
        devices = self._current_audio_devices()
        if action == "back":
            self.screen = Screen.SETTINGS
        elif action == "audio-up":
            self.audio_offset = max(0, self.audio_offset - 1)
        elif action == "audio-down":
            maximum = max(0, len(devices) - self.visible_audio_count)
            self.audio_offset = min(maximum, self.audio_offset + 1)
        elif action.startswith("select-audio:"):
            try:
                index = int(action.split(":", 1)[1])
                device = devices[index]
            except (ValueError, IndexError):
                return
            if self.screen is Screen.AUDIO_PLAYBACK:
                self.selected_playback_device = device.alsa_name
            else:
                self.selected_capture_device = device.alsa_name
            self.screen = Screen.SETTINGS

    def _current_audio_devices(self) -> Sequence[AudioDevice]:
        if self.screen is Screen.AUDIO_PLAYBACK:
            return self.playback_devices
        return self.capture_devices

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
        files = self.filtered_files
        if not 0 <= index < len(files):
            return
        self.selected_file = index
        self._ensure_selection_visible()
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
