from __future__ import annotations

import unittest

try:
    from PIL import Image
except ImportError:  # Pillow is optional outside the rendered touch frontend.
    Image = None

from zxdeck.frontends.touch.frame import crop_rgb565, image_to_rgb565


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

    def test_preconverted_frame_can_be_cropped_by_rows(self) -> None:
        pixels = bytes(range(24))  # 4x3 pixels, two bytes per pixel
        self.assertEqual(
            bytes((2, 3, 4, 5, 10, 11, 12, 13)),
            crop_rgb565(pixels, 4, 1, 0, 2, 2),
        )

    def test_invalid_preconverted_crop_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            crop_rgb565(b"\x00\x00", 1, 1, 0, 1, 1)


if __name__ == "__main__":
    unittest.main()
