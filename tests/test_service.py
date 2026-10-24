from __future__ import annotations

from pathlib import Path
import unittest

from zxdeck.service import render_systemd_splash_unit, render_systemd_unit


class ServiceUnitTests(unittest.TestCase):
    def test_unit_uses_checkout_paths_hardware_groups_and_poweroff_flag(self) -> None:
        unit = render_systemd_unit(Path("/opt/zxdeck"), "deck")

        self.assertIn("User=deck", unit)
        self.assertIn("SupplementaryGroups=spi gpio", unit)
        self.assertIn("WorkingDirectory=/opt/zxdeck", unit)
        self.assertIn("/opt/zxdeck/.venv/bin/python", unit)
        self.assertIn("--allow-poweroff", unit)
        self.assertIn("After=local-fs.target zxdeck-splash.service", unit)
        self.assertIn(
            "ExecStartPre=-+/usr/bin/systemctl stop zxdeck-splash.service",
            unit,
        )
        self.assertNotIn("Conflicts=zxdeck-splash.service", unit)
        self.assertNotIn("Wants=zxdeck-splash.service", unit)
        self.assertIn("WantedBy=multi-user.target", unit)

    def test_splash_unit_runs_before_basic_target(self) -> None:
        unit = render_systemd_splash_unit(Path("/opt/zxdeck"), "deck")

        self.assertIn("Description=ZX Deck early boot splash", unit)
        self.assertIn("DefaultDependencies=no", unit)
        self.assertIn("RequiresMountsFor=/opt/zxdeck", unit)
        self.assertIn("After=systemd-udev-trigger.service", unit)
        self.assertIn("systemd-udevd.service", unit)
        self.assertNotIn("Requires=local-fs.target", unit)
        self.assertIn("Before=basic.target", unit)
        self.assertIn("Type=notify", unit)
        self.assertIn("NotifyAccess=main", unit)
        self.assertIn("User=deck", unit)
        self.assertIn("SupplementaryGroups=spi gpio", unit)
        self.assertIn("/opt/zxdeck/tools/boot_splash.py", unit)
        self.assertIn("--hold", unit)
        self.assertIn("TimeoutStartSec=35", unit)
        self.assertIn("WantedBy=basic.target", unit)


if __name__ == "__main__":
    unittest.main()
