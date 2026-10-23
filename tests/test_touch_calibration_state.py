from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from zxdeck.hardware.config import HardwareConfig


class TouchCalibrationStateTests(unittest.TestCase):
    def test_device_calibration_overrides_repository_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "hardware.toml"
            fallback = root / "fallback.json"
            runtime = root / "touch-calibration.json"
            fallback.write_text("{}", encoding="utf-8")
            runtime.write_text("{}", encoding="utf-8")
            config_path.write_text(
                textwrap.dedent(
                    """
                    [touch]
                    enabled = true
                    calibration_file = "fallback.json"
                    """
                ),
                encoding="utf-8",
            )

            with patch(
                "zxdeck.hardware.config.DEFAULT_TOUCH_CALIBRATION_STATE",
                runtime,
            ):
                config = HardwareConfig.load(config_path)

            self.assertEqual(runtime.resolve(), config.touch.calibration_file)


if __name__ == "__main__":
    unittest.main()
