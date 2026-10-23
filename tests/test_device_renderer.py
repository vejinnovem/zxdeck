from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:
    ImageChops = None

from zxdeck.frontends.touch.device_renderer import DeviceTouchRenderer


@unittest.skipIf(ImageChops is None, "Pillow is not installed")
class DeviceTouchRendererTests(unittest.TestCase):
    def test_settings_shows_supplied_ipv4_without_moving_targets(self) -> None:
        disconnected = DeviceTouchRenderer(address_provider=lambda: None).render_settings()
        connected = DeviceTouchRenderer(
            address_provider=lambda: "192.168.1.84"
        ).render_settings()

        self.assertIsNotNone(
            ImageChops.difference(disconnected.image, connected.image).getbbox()
        )
        self.assertEqual("playback-device", connected.action_at(120, 110))
        self.assertEqual("capture-device", connected.action_at(120, 165))
        self.assertEqual("power", connected.action_at(120, 230))


if __name__ == "__main__":
    unittest.main()
