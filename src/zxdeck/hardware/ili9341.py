"""Small dependency-light ILI9341-compatible SPI driver used by zxdeck."""

from __future__ import annotations

import time
from typing import Any, Callable

from .config import DisplayConfig


class ILI9341:
    def __init__(
        self,
        config: DisplayConfig,
        *,
        spi_factory: Callable[[], Any] | None = None,
        output_factory: Callable[..., Any] | None = None,
    ) -> None:
        if not config.enabled:
            raise ValueError("display is disabled in the hardware configuration")
        if spi_factory is None:
            import spidev

            spi_factory = spidev.SpiDev
        if output_factory is None:
            from .gpio import LgpioOutputDevice

            output_factory = LgpioOutputDevice

        self.config = config
        self.dc = output_factory(config.dc_bcm, initial_value=False)
        self.reset = output_factory(config.reset_bcm, initial_value=True)
        self.spi = spi_factory()
        self.spi.open(config.spi_bus, config.spi_device)
        self.spi.mode = 0
        self.spi.max_speed_hz = config.speed_hz
        self.spi.bits_per_word = 8

    def close(self) -> None:
        self.spi.close()
        self.dc.close()
        self.reset.close()

    def hardware_reset(self) -> None:
        self.reset.on()
        time.sleep(0.01)
        self.reset.off()
        time.sleep(0.02)
        self.reset.on()
        time.sleep(0.15)

    def command(self, value: int, data: bytes = b"") -> None:
        self.dc.off()
        self.spi.writebytes([value])
        if data:
            self.dc.on()
            self.spi.writebytes2(data)

    def read_register(self, register: int, length: int) -> bytes:
        self.dc.off()
        self.spi.writebytes([register])
        self.dc.on()
        return bytes(self.spi.xfer2([0] * length))

    def initialize(self) -> None:
        self.hardware_reset()
        self.command(0x01)
        time.sleep(0.15)
        self.command(0x28)
        sequence = (
            (0xCF, b"\x00\xC1\x30"),
            (0xED, b"\x64\x03\x12\x81"),
            (0xE8, b"\x85\x00\x78"),
            (0xCB, b"\x39\x2C\x00\x34\x02"),
            (0xF7, b"\x20"),
            (0xEA, b"\x00\x00"),
            (0xC0, b"\x23"),
            (0xC1, b"\x10"),
            (0xC5, b"\x3E\x28"),
            (0xC7, b"\x86"),
            (0x36, b"\x48"),
            (0x3A, b"\x55"),
            (0xB1, b"\x00\x18"),
            (0xB6, b"\x08\x82\x27"),
            (0xF2, b"\x00"),
            (0x26, b"\x01"),
            (0xE0, b"\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00"),
            (0xE1, b"\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F"),
        )
        for register, data in sequence:
            self.command(register, data)
        self.command(0x11)
        time.sleep(0.15)
        self.command(0x29)
        time.sleep(0.05)

    def set_window(self, x0: int, y0: int, x1: int, y1: int) -> None:
        self.command(0x2A, bytes((x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF)))
        self.command(0x2B, bytes((y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF)))
        self.command(0x2C)

    def write_rgb565(self, pixels: bytes | bytearray) -> None:
        self.dc.on()
        self.spi.writebytes2(pixels)

    def fill(self, color: int) -> None:
        self.fill_rect(0, 0, self.config.width, self.config.height, color)

    def fill_rect(self, x: int, y: int, width: int, height: int, color: int) -> None:
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.config.width, x + width)
        y1 = min(self.config.height, y + height)
        if x0 >= x1 or y0 >= y1:
            return
        self.set_window(x0, y0, x1 - 1, y1 - 1)
        pixel = bytes((color >> 8, color & 0xFF))
        self.write_rgb565(pixel * ((x1 - x0) * (y1 - y0)))

