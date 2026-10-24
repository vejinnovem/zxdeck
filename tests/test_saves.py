from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from zxdeck.config import StorageConfig
from zxdeck.frontends.touch.device_controller import DeviceTouchUIController, SAVES_SCREEN
from zxdeck.frontends.touch.renderer import Screen
from zxdeck.storage import TapeLibrary, list_save_entries


class SaveLibraryTests(unittest.TestCase):
    def test_main_library_prunes_top_level_saves_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "GAME.TAP").write_bytes(b"")
            saves = root / "saves"
            saves.mkdir()
            (saves / "slot1.tap").write_bytes(b"")
            (saves / "slot2.wav").write_bytes(b"")

            library = TapeLibrary(StorageConfig(path=root, recursive=True))
            entries = library.refresh()
            save_entries = list_save_entries(root)

            self.assertEqual(("GAME.TAP",), tuple(entry.name for entry in entries))
            self.assertEqual(
                ("slot1.tap", "slot2.wav"),
                tuple(entry.name for entry in save_entries),
            )

    def test_saves_action_opens_dedicated_browser_and_selects_save_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            saves = root / "saves"
            saves.mkdir()
            save_path = saves / "rpg-slot.tap"
            save_path.write_bytes(b"")

            controller = DeviceTouchUIController((), selected_storage_path=root)
            controller.screen = Screen.SEARCH
            controller.handle_action("saves")

            self.assertEqual(SAVES_SCREEN, controller.screen)
            self.assertEqual(("rpg-slot.tap",), tuple(controller.save_files))

            controller.handle_action("open-save:0")

            self.assertEqual(Screen.HOME, controller.screen)
            self.assertEqual(save_path, controller.selected_tape_path)
            self.assertEqual("rpg-slot.tap", controller.state.tape_name)


if __name__ == "__main__":
    unittest.main()
