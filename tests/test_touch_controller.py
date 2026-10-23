from __future__ import annotations

import unittest

from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import Screen, TouchUIController


FILES = tuple(f"GAME {index}.TZX" for index in range(7))


class TouchUIControllerTests(unittest.TestCase):
    def test_transport_actions_update_mock_state(self) -> None:
        controller = TouchUIController(
            FILES,
            state=DeckState(position_seconds=42),
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
        controller = TouchUIController(FILES)
        controller.handle_action("new")
        self.assertEqual(Screen.FILENAME, controller.screen)

        controller.handle_action("key:2")
        controller.handle_action("key:2")
        controller.handle_action("key:3")
        controller.handle_action("save")

        self.assertEqual(Screen.HOME, controller.screen)
        self.assertEqual("BD.TZX", controller.state.tape_name)

    def test_settings_and_filename_cancel_return_home(self) -> None:
        controller = TouchUIController(FILES)
        controller.handle_action("settings")
        controller.handle_action("back")
        self.assertEqual(Screen.HOME, controller.screen)

        controller.handle_action("new")
        controller.handle_action("cancel")
        self.assertEqual(Screen.HOME, controller.screen)


if __name__ == "__main__":
    unittest.main()
