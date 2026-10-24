from __future__ import annotations

import unittest

try:
    from PIL import Image
except ImportError:
    Image = None

from zxdeck.core.state import DeckState
from zxdeck.frontends.touch.renderer import BLACK, RED
from zxdeck.frontends.touch.runtime_renderer import DeviceTouchRenderer


@unittest.skipIf(Image is None, "Pillow is not installed")
class RuntimeProgressRendererTests(unittest.TestCase):
    def test_elapsed_and_remaining_halves_split_inside_one_stripe(self) -> None:
        renderer = DeviceTouchRenderer()
        image = Image.new("RGB", (240, 320), BLACK)
        state = DeckState(position_seconds=25.0, duration_seconds=100.0)

        renderer.decorate_signal_progress(
            image,
            state,
            phase="pilot",
            animation_step=0,
        )

        # Progress inner track starts at x=17 and is 207 px wide.  At 25%,
        # the playhead falls at x=68, inside the red stripe spanning x=65..72.
        # Pixels on the left must stay bright; pixels on the right must already
        # be dim.  The exact boundary pixel is the white playhead.
        self.assertEqual(RED, image.getpixel((67, 85)))
        self.assertEqual(tuple(channel // 4 for channel in RED), image.getpixel((69, 85)))
        self.assertEqual((245, 245, 245), image.getpixel((68, 85)))


if __name__ == "__main__":
    unittest.main()
