from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from zxdeck.config import AppConfig


class AppConfigTests(unittest.TestCase):
    def test_relative_storage_path_and_extensions_are_normalised(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "application.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    [storage]
                    path = "tapes"
                    browse_root = "."
                    extensions = ["TAP", ".TZX"]
                    require_mount = true
                    mount_path = "media"

                    [audio]
                    capture_device = "plughw:CARD=USB,DEV=0"
                    playback_device = "default"
                    """
                ),
                encoding="utf-8",
            )

            config = AppConfig.load(config_path)

            self.assertEqual(root / "tapes", config.storage.path)
            self.assertEqual((".tap", ".tzx"), config.storage.extensions)
            self.assertTrue(config.storage.require_mount)
            self.assertEqual(root, config.storage.browse_root)
            self.assertEqual(root / "media", config.storage.mount_path)
            self.assertEqual(
                "plughw:CARD=USB,DEV=0",
                config.audio.capture_device,
            )
