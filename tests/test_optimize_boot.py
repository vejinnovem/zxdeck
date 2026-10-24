from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.optimize_boot import OPTIONAL_UNITS, apply_optimizations, restore_defaults


class BootOptimizationTests(unittest.TestCase):
    def test_apply_writes_marker_and_swap_override(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "cloud" / "cloud-init.disabled"
            target = root / "rpi" / "swap.conf.d" / "90-zxdeck.conf"
            source = root / "source.conf"
            source.write_text("[Main]\nMechanism=zram\n", encoding="utf-8")
            with patch("tools.optimize_boot.subprocess.run") as run:
                apply_optimizations(marker, target, source)

            self.assertEqual(marker.read_bytes(), b"")
            self.assertEqual(target.read_text(encoding="utf-8"), source.read_text(encoding="utf-8"))
            run.assert_called_once_with(("systemctl", "disable", *OPTIONAL_UNITS), check=True)

    def test_restore_removes_overrides_and_enables_units(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / "cloud-init.disabled"
            swap = root / "90-zxdeck.conf"
            marker.touch()
            swap.touch()
            with patch("tools.optimize_boot.subprocess.run") as run:
                restore_defaults(marker, swap)

            self.assertFalse(marker.exists())
            self.assertFalse(swap.exists())
            run.assert_called_once_with(("systemctl", "enable", *OPTIONAL_UNITS), check=True)


if __name__ == "__main__":
    unittest.main()
