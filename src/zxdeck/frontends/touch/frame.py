"""Conversion helpers between rendered UI frames and the SPI LCD format."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image


_RED_HIGH = tuple(value & 0xF8 for value in range(256))
_GREEN_HIGH = tuple(value >> 5 for value in range(256))
_GREEN_LOW = tuple((value & 0x1C) << 3 for value in range(256))
_BLUE_LOW = tuple(value >> 3 for value in range(256))


def image_to_rgb565(image: "Image") -> bytes:
    """Convert a Pillow image to big-endian RGB565 expected by the LCD driver."""
    from PIL import Image, ImageChops

    rgb = image.convert("RGB")
    red, green, blue = rgb.split()
    high = ImageChops.add(red.point(_RED_HIGH), green.point(_GREEN_HIGH))
    low = ImageChops.add(green.point(_GREEN_LOW), blue.point(_BLUE_LOW))

    # LA stores its two 8-bit channels interleaved, which is exactly the byte
    # layout needed here: high byte followed by low byte for every pixel.
    return Image.merge("LA", (high, low)).tobytes()
