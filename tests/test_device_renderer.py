from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:
    ImageChops = None

from zxdeck.core.state import DeckState
from zxdeck.frontends.touch import DeviceTouchRenderer
from zxdeck.frontends.touch.renderer import DIM, WHITE


@unittest.skipIf(ImageChops is None, "Pillow is not installed")
class DeviceTouchRendererTests(unittest.TestCase):
    def test_settings_shows_supplied_ipv4_without_moving_targets(self) -> None:
        disconnected = DeviceTouchRenderer(address_provider=lambda: None).render_settings()
        connected_renderer = DeviceTouchRenderer(address_provider=lambda: "192.168.1.84")
        connected = connected_renderer.render_settings()
        connected_last_page = connected_renderer.render_settings(offset=4)
        self.assertIsNotNone(ImageChops.difference(disconnected.image, connected.image).getbbox())
        self.assertEqual("playback-device", connected.action_at(120, 110))
        self.assertEqual("capture-device", connected.action_at(120, 165))
        self.assertEqual("output-level", connected.action_at(120, 230))
        self.assertEqual("power", connected_last_page.action_at(120, 230))

    def test_home_exposes_previous_play_next_stop_and_record(self) -> None:
        renderer = DeviceTouchRenderer()
        screen = renderer.render_home(
            DeckState(
                tape_name="RING.TZX",
                segment_label="PROGRAM RING",
                segment_index=1,
                segment_count=4,
            )
        )

        self.assertEqual("rewind", screen.action_at(45, 150))
        self.assertEqual("play", screen.action_at(120, 150))
        self.assertEqual("forward", screen.action_at(195, 150))
        self.assertEqual("stop", screen.action_at(64, 205))
        self.assertEqual("record", screen.action_at(176, 205))

    def test_home_draws_segment_ticks_at_timeline_positions(self) -> None:
        renderer = DeviceTouchRenderer()
        screen = renderer.render_home(
            DeckState(
                tape_name="RING.TZX",
                duration_seconds=10.0,
                segment_index=2,
                segment_count=2,
                segment_starts=(0.0, 5.0),
            )
        )

        self.assertEqual(DIM, screen.image.getpixel((17, 79)))
        self.assertEqual(WHITE, screen.image.getpixel((120, 79)))


if __name__ == "__main__":
    unittest.main()
