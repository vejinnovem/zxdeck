from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:
    ImageChops = None

from zxdeck.frontends.touch import DeviceTouchRenderer


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


if __name__ == "__main__":
    unittest.main()
