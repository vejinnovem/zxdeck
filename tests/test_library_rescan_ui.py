from __future__ import annotations

import unittest

from zxdeck.frontends.touch import TouchUIController


class LibraryRescanUITests(unittest.TestCase):
    def test_settings_pages_advance_by_four_to_rescan_page(self) -> None:
        controller = TouchUIController(("GAME.TZX",))
        controller.handle_action("settings")

        controller.handle_action("settings-down")
        self.assertEqual(4, controller.settings_offset)
        controller.handle_action("settings-down")
        self.assertEqual(8, controller.settings_offset)
        controller.handle_action("settings-down")
        self.assertEqual(8, controller.settings_offset)

        controller.handle_action("settings-up")
        self.assertEqual(4, controller.settings_offset)

    def test_rescan_action_sets_runtime_request_flag(self) -> None:
        controller = TouchUIController(("GAME.TZX",))
        controller.handle_action("settings")
        controller.handle_action("rescan-library")

        self.assertTrue(controller.library_rescan_requested)


if __name__ == "__main__":
    unittest.main()
