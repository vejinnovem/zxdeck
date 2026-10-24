from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from zxdeck.core.state import DeckState, TransportState
from zxdeck.audio import AudioDevice
from zxdeck.frontends.touch import Screen, TouchUIController
from zxdeck.storage import DirectoryBrowser


FILES = tuple(f"GAME {index}.TZX" for index in range(7))


class TouchUIControllerTests(unittest.TestCase):
    def test_transport_actions_keep_unimplemented_recording_stopped(self) -> None:
        controller = TouchUIController(
            FILES,
            state=DeckState(position_seconds=42, tape_name="GAME 0.TZX"),
        )

        controller.handle_action("play")
        self.assertEqual(TransportState.PLAYING, controller.state.transport)
        controller.handle_action("record")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("REC NOT IMPLEMENTED", controller.state.error)
        controller.handle_action("rewind")
        self.assertEqual(0, controller.state.position_seconds)
        controller.handle_action("stop")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual(5, controller.state.revision)

    def test_play_and_record_require_a_selected_or_named_tape(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("play")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("SELECT A TAPE", controller.state.error)

        controller.handle_action("record")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("REC NOT IMPLEMENTED", controller.state.error)

    def test_seventh_file_can_be_reached_and_opened(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("files")
        for _ in range(6):
            controller.handle_action("down")

        self.assertEqual(Screen.FILES, controller.screen)
        self.assertEqual(6, controller.selected_file)
        self.assertEqual(1, controller.file_offset)

        controller.handle_action("open-selected")
        self.assertEqual(Screen.HOME, controller.screen)
        self.assertEqual("GAME 6.TZX", controller.state.tape_name)

    def test_file_buttons_scroll_by_visible_page(self) -> None:
        files = tuple(f"GAME {index:02d}.TZX" for index in range(20))
        controller = TouchUIController(files)
        controller.handle_action("files")

        controller.handle_action("down")
        self.assertEqual(6, controller.selected_file)
        self.assertEqual(6, controller.file_offset)

        controller.handle_action("down")
        self.assertEqual(12, controller.selected_file)
        self.assertEqual(12, controller.file_offset)

        controller.handle_action("up")
        self.assertEqual(6, controller.selected_file)
        self.assertEqual(6, controller.file_offset)

    def test_file_group_jump_skips_whole_letter_group(self) -> None:
        controller = TouchUIController(
            ("1942.TAP", "ALPHA.TAP", "ARCADE.TAP", "BETA.TZX", "BRAVO.TAP", "ZED.TAP")
        )
        controller.handle_action("files")
        controller.handle_action("down")
        self.assertEqual(1, controller.selected_file)

        controller.handle_action("group-down")
        self.assertEqual(3, controller.selected_file)
        self.assertEqual(3, controller.file_offset)
        controller.handle_action("group-up")
        self.assertEqual(1, controller.selected_file)

    def test_tapped_file_is_opened_and_invalid_index_is_ignored(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("files")
        controller.handle_action("open:not-a-number")
        controller.handle_action("open:99")
        self.assertEqual(Screen.FILES, controller.screen)

        controller.handle_action("open:2")
        self.assertEqual(Screen.HOME, controller.screen)
        self.assertEqual("GAME 2.TZX", controller.state.tape_name)

    def test_filename_keypad_saves_name_with_default_extension(self) -> None:
        controller = TouchUIController(
            FILES,
            state=DeckState(transport=TransportState.RECORDING),
        )
        controller.handle_action("new")
        self.assertEqual(Screen.FILENAME, controller.screen)
        self.assertEqual(TransportState.STOPPED, controller.state.transport)

        controller.handle_action("key:2")
        controller.handle_action("key:2")
        controller.handle_action("key:3")
        controller.handle_action("save")

        self.assertEqual(Screen.HOME, controller.screen)
        self.assertEqual("BD.TZX", controller.state.tape_name)
        self.assertEqual(TransportState.STOPPED, controller.state.transport)

    def test_settings_and_filename_cancel_return_home(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("settings")
        controller.handle_action("back")
        self.assertEqual(Screen.HOME, controller.screen)

        controller.handle_action("new")
        controller.handle_action("cancel")
        self.assertEqual(Screen.HOME, controller.screen)

    def test_settings_scroll_and_output_level_controls(self) -> None:
        controller = TouchUIController(FILES, output_level=25, previous_output_level=25)
        controller.handle_action("settings")
        controller.handle_action("settings-down")
        self.assertEqual(4, controller.settings_offset)
        controller.handle_action("settings-up")
        self.assertEqual(0, controller.settings_offset)
        controller.handle_action("output-level")
        self.assertEqual(Screen.OUTPUT_LEVEL, controller.screen)
        controller.handle_action("volume-up")
        self.assertEqual(30, controller.output_level)
        controller.handle_action("volume-mute")
        self.assertEqual(0, controller.output_level)
        controller.handle_action("volume-mute")
        self.assertEqual(30, controller.output_level)

    def test_search_filters_virtual_file_list(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("files")
        controller.handle_action("search")
        controller.editor.text = "GAME 6"
        controller.editor.commit_pending()
        controller.handle_action("apply-search")

        self.assertEqual(Screen.FILES, controller.screen)
        self.assertEqual(("GAME 6.TZX",), controller.filtered_files)
        controller.handle_action("open:0")
        self.assertEqual("GAME 6.TZX", controller.state.tape_name)

    def test_search_keeps_selected_file_path(self) -> None:
        paths = tuple(Path("/tapes") / name for name in FILES)
        controller = TouchUIController(FILES, file_paths=paths)
        controller.search_query = "GAME 6"
        controller.handle_action("files")
        controller.handle_action("open:0")

        self.assertEqual(paths[6], controller.selected_tape_path)

    def test_letter_grid_jumps_to_first_file_in_virtual_group(self) -> None:
        files = ("1942.TAP", "ALPHA.TAP", "BETA.TZX", "BRAVO.TAP", "ZED.TAP")
        controller = TouchUIController(files)
        controller.handle_action("files")
        controller.handle_action("search")
        controller.editor.text = "old search"
        controller.handle_action("letters")

        self.assertEqual(Screen.LETTERS, controller.screen)
        controller.handle_action("jump:B")

        self.assertEqual(Screen.FILES, controller.screen)
        self.assertEqual("", controller.search_query)
        self.assertEqual(2, controller.selected_file)
        self.assertEqual(2, controller.file_offset)

    def test_hash_group_and_letter_grid_back_action(self) -> None:
        controller = TouchUIController(("1942.TAP", "ALPHA.TAP"))
        controller.screen = Screen.LETTERS
        controller.handle_action("back")
        self.assertEqual(Screen.SEARCH, controller.screen)

        controller.screen = Screen.LETTERS
        controller.handle_action("jump:#")
        self.assertEqual(Screen.FILES, controller.screen)
        self.assertEqual(0, controller.selected_file)

    def test_directory_picker_is_constrained_and_selects_current_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            games = root / "Games"
            games.mkdir()
            controller = TouchUIController(
                FILES,
                directory_browser=DirectoryBrowser(root),
            )

            controller.handle_action("settings")
            controller.handle_action("directories")
            controller.handle_action("directory:0")
            controller.handle_action("use-directory")

            self.assertEqual(Screen.SETTINGS, controller.screen)
            self.assertEqual(games, controller.selected_storage_path)

    def test_poweroff_requires_settings_and_confirmation(self) -> None:
        controller = TouchUIController(
            FILES,
            state=DeckState(transport=TransportState.RECORDING),
        )
        controller.handle_action("settings")
        controller.handle_action("power")
        self.assertEqual(Screen.POWER, controller.screen)
        self.assertFalse(controller.shutdown_requested)

        controller.handle_action("confirm-poweroff")
        self.assertTrue(controller.shutdown_requested)
        self.assertEqual(TransportState.STOPPED, controller.state.transport)

    def test_audio_device_pickers_save_playback_and_capture_choices(self) -> None:
        playback = AudioDevice("USB output", "plughw:CARD=USB,DEV=0")
        capture = AudioDevice("USB input", "plughw:CARD=USB,DEV=1")
        controller = TouchUIController(
            FILES,
            playback_devices=(playback,),
            capture_devices=(capture,),
        )

        controller.handle_action("settings")
        controller.handle_action("playback-device")
        self.assertEqual(Screen.AUDIO_PLAYBACK, controller.screen)
        controller.handle_action("select-audio:0")
        self.assertEqual(playback.alsa_name, controller.selected_playback_device)
        self.assertEqual(Screen.SETTINGS, controller.screen)

        controller.handle_action("capture-device")
        controller.handle_action("select-audio:0")
        self.assertEqual(capture.alsa_name, controller.selected_capture_device)


if __name__ == "__main__":
    unittest.main()
