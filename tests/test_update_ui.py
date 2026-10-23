from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:
    ImageChops = None

from zxdeck.frontends.touch import DeviceTouchRenderer, Screen, TouchUIController


class UpdateNavigationTests(unittest.TestCase):
    def test_updates_is_a_sixth_scrollable_settings_entry(self) -> None:
        controller = TouchUIController(())
        controller.handle_action("settings")
        self.assertEqual(Screen.SETTINGS, controller.screen)
        self.assertEqual(6, controller.settings_entry_count)
        controller.handle_action("updates")
        self.assertEqual("updates", controller.screen)
        controller.handle_action("back")
        self.assertEqual(Screen.SETTINGS, controller.screen)


@unittest.skipIf(ImageChops is None, "Pillow is not installed")
class UpdateRendererTests(unittest.TestCase):
    def test_second_settings_page_exposes_updates_and_power(self) -> None:
        renderer = DeviceTouchRenderer(address_provider=lambda: "192.168.1.84")
        second_page = renderer.render_settings(offset=2)
        self.assertEqual("updates", second_page.action_at(120, 165))
        self.assertEqual("power", second_page.action_at(120, 220))
        self.assertEqual("back", second_page.action_at(40, 295))
        self.assertEqual("settings-up", second_page.action_at(120, 295))
        self.assertEqual("settings-down", second_page.action_at(200, 295))

    def test_update_button_is_only_active_when_fast_forward_is_available(self) -> None:
        renderer = DeviceTouchRenderer()
        current = renderer.render_updates(installed_version="12345678", available_version="12345678", status="UP TO DATE", can_install=False)
        available = renderer.render_updates(installed_version="12345678", available_version="abcdef12", status="UPDATE AVAILABLE", can_install=True)
        self.assertIsNone(current.action_at(200, 295))
        self.assertEqual("check-update", current.action_at(120, 295))
        self.assertEqual("install-update", available.action_at(200, 295))


if __name__ == "__main__":
    unittest.main()
