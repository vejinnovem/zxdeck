from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

from zxdeck.hardware.calibration import TouchCalibration, fit_calibration
from zxdeck.hardware.config import HardwareConfig, TouchConfig
from zxdeck.hardware.gpio import LgpioInputDevice, LgpioOutputDevice
from zxdeck.hardware.xpt2046 import XPT2046


class HardwareConfigTests(unittest.TestCase):
    def test_disabled_display_is_valid_and_relative_calibration_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "hardware.toml"
            path.write_text(
                textwrap.dedent(
                    """
                    [display]
                    enabled = false
                    [touch]
                    enabled = false
                    calibration_file = "calibration.json"
                    """
                ),
                encoding="utf-8",
            )
            config = HardwareConfig.load(path)
            self.assertFalse(config.display.enabled)
            self.assertFalse(config.touch.enabled)
            self.assertEqual(root / "calibration.json", config.touch.calibration_file)


class CalibrationTests(unittest.TestCase):
    def test_validated_zxdeck_samples_fit_expected_orientation(self) -> None:
        targets = [(20, 20), (219, 20), (219, 299), (20, 299), (120, 160)]
        samples = [(566, 3774), (3490, 3696), (3519, 662), (444, 515), (2033, 2171)]
        calibration, rejected = fit_calibration(targets, samples)
        self.assertEqual(set(), rejected)
        self.assertEqual("raw_x", calibration.x_axis)
        self.assertEqual("raw_y", calibration.y_axis)
        self.assertGreater(calibration.x_slope, 0)
        self.assertLess(calibration.y_slope, 0)
        self.assertEqual((121, 159), calibration.map(2033, 2171, 240, 320))

    def test_single_bad_corner_is_rejected(self) -> None:
        targets = [(20, 20), (219, 20), (219, 299), (20, 299), (120, 160)]
        samples = [(692, 3700), (3551, 3735), (3543, 604), (1863, 824), (2066, 2197)]
        _calibration, rejected = fit_calibration(targets, samples)
        self.assertEqual({3}, rejected)

    def test_json_round_trip(self) -> None:
        original = TouchCalibration(1, "raw_x", "raw_y", 1.0, 2.0, -1.0, 3.0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "calibration.json"
            original.save(path)
            self.assertEqual(original, TouchCalibration.load(path))


class FakeSpi:
    def __init__(self) -> None:
        self.responses = iter(([0, 10, 0], [0, 20, 0]) * 3)
        self.opened: tuple[int, int] | None = None

    def open(self, bus: int, device: int) -> None:
        self.opened = (bus, device)

    def xfer2(self, _data: list[int]) -> list[int]:
        return list(next(self.responses))

    def close(self) -> None:
        pass


class FakeInput:
    is_active = True

    def __init__(self, pin: int, pull_up: bool) -> None:
        self.pin = pin
        self.pull_up = pull_up

    def close(self) -> None:
        pass


class XPT2046Tests(unittest.TestCase):
    def test_driver_uses_config_and_median_sampling(self) -> None:
        spi = FakeSpi()
        touch = XPT2046(
            TouchConfig(enabled=True),
            spi_factory=lambda: spi,
            input_factory=FakeInput,
        )
        self.assertEqual((0, 1), spi.opened)
        self.assertTrue(touch.pressed)
        self.assertEqual((320, 640), touch.read_raw(samples=3))


class FakeLgpio:
    SET_PULL_UP = 32
    SET_PULL_NONE = 128

    def __init__(self) -> None:
        self.levels: dict[int, int] = {}
        self.claimed_input: tuple[int, int] | None = None
        self.closed = False

    def gpiochip_open(self, chip: int) -> int:
        self.chip = chip
        return 7

    def gpio_claim_input(self, _handle: int, pin: int, flags: int) -> None:
        self.claimed_input = (pin, flags)

    def gpio_claim_output(self, _handle: int, pin: int, level: int) -> None:
        self.levels[pin] = level

    def gpio_read(self, _handle: int, pin: int) -> int:
        return self.levels.get(pin, 1)

    def gpio_write(self, _handle: int, pin: int, level: int) -> None:
        self.levels[pin] = level

    def gpio_free(self, _handle: int, _pin: int) -> None:
        pass

    def gpiochip_close(self, _handle: int) -> None:
        self.closed = True


class LgpioDeviceTests(unittest.TestCase):
    def test_active_low_input_is_polled_without_callbacks(self) -> None:
        module = FakeLgpio()
        device = LgpioInputDevice(23, pull_up=True, module=module)
        self.assertEqual((23, module.SET_PULL_UP), module.claimed_input)
        self.assertFalse(device.is_active)
        module.levels[23] = 0
        self.assertTrue(device.is_active)
        device.close()
        self.assertTrue(module.closed)

    def test_output_supports_on_and_off(self) -> None:
        module = FakeLgpio()
        device = LgpioOutputDevice(25, initial_value=True, module=module)
        self.assertEqual(1, module.levels[25])
        device.off()
        self.assertEqual(0, module.levels[25])
        device.on()
        self.assertEqual(1, module.levels[25])
        device.close()


if __name__ == "__main__":
    unittest.main()

