from __future__ import annotations

from pathlib import Path
import unittest

from zxdeck.service import render_systemd_unit


class ServiceUnitTests(unittest.TestCase):
    def test_unit_uses_checkout_paths_hardware_groups_and_poweroff_flag(self) -> None:
        unit = render_systemd_unit(Path("/opt/zxdeck"), "deck")

        self.assertIn("User=deck", unit)
        self.assertIn("SupplementaryGroups=spi gpio", unit)
        self.assertIn("WorkingDirectory=/opt/zxdeck", unit)
        self.assertIn("/opt/zxdeck/.venv/bin/python", unit)
        self.assertIn("--allow-poweroff", unit)
        self.assertIn("WantedBy=multi-user.target", unit)


if __name__ == "__main__":
    unittest.main()
