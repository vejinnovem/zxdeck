from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import Screen, TouchUIController
from zxdeck.storage import DirectoryBrowser


FILES = tuple(f"GAME {index}.TZX" for index in range(7))


class TouchUIControllerTests(unittest.TestCase):
    def test_transport_actions_update_mock_state(self) -> None:
        controller = TouchUIController(
            FILES,
            state=DeckState(position_seconds=42, tape_name="GAME 0.TZX"),
        )

        controller.handle_action("play")
        self.assertEqual(TransportState.PLAYING, controller.state.transport)
        controller.handle_action("record")
        self.assertEqual(TransportState.RECORDING, controller.state.transport)
        controller.handle_action("rewind")
        self.assertEqual(0, controller.state.position_seconds)
        controller.handle_action("stop")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual(4, controller.state.revision)

    def test_play_and_record_require_a_selected_or_named_tape(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("play")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("SELECT A TAPE", controller.state.error)

        controller.handle_action("record")
        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("NAME THE TAPE", controller.state.error)

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


if __name__ == "__main__":
    unittest.main()
