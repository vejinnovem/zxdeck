"""XPT2046 SPI touchscreen reader."""

from __future__ import annotations

import statistics
from typing import Any, Callable

from .config import TouchConfig


class XPT2046:
    def __init__(
        self,
        config: TouchConfig,
        *,
        spi_factory: Callable[[], Any] | None = None,
        input_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not config.enabled:
            raise ValueError("touchscreen is disabled in the hardware configuration")
        if spi_factory is None:
            import spidev

            spi_factory = spidev.SpiDev
        if input_factory is None:
            from gpiozero import DigitalInputDevice

            input_factory = DigitalInputDevice

        self.config = config
        self.irq = input_factory(config.irq_bcm, pull_up=True)
        self.spi = spi_factory()
        self.spi.open(config.spi_bus, config.spi_device)
        self.spi.mode = 0
        self.spi.max_speed_hz = config.speed_hz
        self.spi.bits_per_word = 8

    @property
    def pressed(self) -> bool:
        return self.irq.is_active

    def _convert(self, command: int) -> int:
        reply = self.spi.xfer2([command, 0x00, 0x00])
        return ((reply[1] << 8) | reply[2]) >> 3

    def read_raw(self, samples: int = 5) -> tuple[int, int]:
        if samples < 1:
            raise ValueError("samples must be positive")
        xs: list[int] = []
        ys: list[int] = []
        for _ in range(samples):
            xs.append(self._convert(0xD0))
            ys.append(self._convert(0x90))
        return int(statistics.median(xs)), int(statistics.median(ys))

    def close(self) -> None:
        self.spi.close()
        self.irq.close()

