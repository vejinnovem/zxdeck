from __future__ import annotations

import unittest

try:
    from PIL import Image
except ImportError:  # Pillow is optional outside the rendered touch frontend.
    Image = None

from zxdeck.frontends.touch.frame import image_to_rgb565


@unittest.skipIf(Image is None, "Pillow is not installed")
class RGB565FrameTests(unittest.TestCase):
    def test_known_colors_are_big_endian_rgb565(self) -> None:
        image = Image.new("RGB", (6, 1))
        image.putdata(
            (
                (0, 0, 0),
                (255, 255, 255),
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
                (123, 45, 67),
            )
        )

        self.assertEqual(
            bytes.fromhex("0000 ffff f800 07e0 001f 7968"),
            image_to_rgb565(image),
        )


if __name__ == "__main__":
    unittest.main()
