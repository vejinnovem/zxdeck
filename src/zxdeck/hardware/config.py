"""Explicit hardware configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True, slots=True)
class DisplayConfig:
    enabled: bool = False
    width: int = 240
    height: int = 320
    spi_bus: int = 0
    spi_device: int = 0
    speed_hz: int = 16_000_000
    dc_bcm: int = 24
    reset_bcm: int = 25


@dataclass(frozen=True, slots=True)
class TouchConfig:
    enabled: bool = False
    spi_bus: int = 0
    spi_device: int = 1
    speed_hz: int = 2_000_000
    irq_bcm: int = 23
    calibration_file: Path | None = None


@dataclass(frozen=True, slots=True)
class HardwareConfig:
    display: DisplayConfig = DisplayConfig()
    touch: TouchConfig = TouchConfig()

    @classmethod
    def load(cls, path: str | Path) -> "HardwareConfig":
        config_path = Path(path).expanduser().resolve()
        with config_path.open("rb") as stream:
            data = tomllib.load(stream)
        display_data = data.get("display", {})
        touch_data = dict(data.get("touch", {}))
        calibration = touch_data.get("calibration_file")
        if calibration:
            calibration_path = Path(calibration).expanduser()
            if not calibration_path.is_absolute():
                calibration_path = config_path.parent / calibration_path
            touch_data["calibration_file"] = calibration_path.resolve()
        return cls(
            display=DisplayConfig(**display_data),
            touch=TouchConfig(**touch_data),
        )

