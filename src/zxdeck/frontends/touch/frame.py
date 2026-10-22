"""Conversion helpers between rendered UI frames and the SPI LCD format."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image


def image_to_rgb565(image: "Image") -> bytes:
    """Convert a Pillow image to big-endian RGB565 expected by the LCD driver."""
    rgb = image.convert("RGB")
    output = bytearray(rgb.width * rgb.height * 2)
    write_at = 0
    for red, green, blue in rgb.getdata():
        value = ((red & 0xF8) << 8) | ((green & 0xFC) << 3) | (blue >> 3)
        output[write_at] = value >> 8
        output[write_at + 1] = value & 0xFF
        write_at += 2
    return bytes(output)
