from __future__ import annotations

import unittest
from unittest.mock import patch

from zxdeck.audio import HardwareOutputState
from zxdeck.frontends.touch.device_controller import (
    DeviceTouchUIController,
    WIFI_NETWORKS_SCREEN,
    WIFI_PASSWORD_SCREEN,
)
from zxdeck.frontends.touch.renderer import Screen
from zxdeck.system import WifiNetwork


class DeviceSettingsControllerTests(unittest.TestCase):
    @patch("zxdeck.frontends.touch.device_controller.hardware_output_state")
    def test_hardware_output_uses_separate_level_mode(self, state) -> None:
        state.return_value = HardwareOutputState("hw:CARD=Device", "Speaker", 70)
        controller = DeviceTouchUIController(())
        controller.handle_action("settings")
        controller.handle_action("hardware-output")

        self.assertEqual(Screen.OUTPUT_LEVEL, controller.screen)
        self.assertEqual("hardware", controller.output_level_mode)
        self.assertEqual(70, controller.previous_hardware_output_level)

        controller.handle_action("back")
        self.assertEqual(Screen.SETTINGS, controller.screen)

    @patch("zxdeck.frontends.touch.device_controller.set_hardware_output_level")
    @patch("zxdeck.frontends.touch.device_controller.hardware_output_state")
    def test_hardware_output_volume_action_changes_card_mixer(self, state, set_level) -> None:
        state.return_value = HardwareOutputState("hw:CARD=Device", "Speaker", 70)
        set_level.return_value = HardwareOutputState("hw:CARD=Device", "Speaker", 75)
        controller = DeviceTouchUIController(())
        controller.screen = Screen.OUTPUT_LEVEL
        controller.output_level_mode = "hardware"

        controller.handle_action("volume-up")

        set_level.assert_called_once_with("default", 75)
        self.assertEqual(75, controller.previous_hardware_output_level)

    @patch("zxdeck.frontends.touch.device_controller.scan_wifi_networks")
    def test_secured_wifi_opens_password_editor(self, scan) -> None:
        scan.return_value = (WifiNetwork("Home", 80, "WPA2"),)
        controller = DeviceTouchUIController(())
        controller.handle_action("settings")
        controller.handle_action("wifi")

        self.assertEqual(WIFI_NETWORKS_SCREEN, controller.screen)
        controller.handle_action("select-wifi:0")
        self.assertEqual(WIFI_PASSWORD_SCREEN, controller.screen)
        self.assertEqual("Home", controller.pending_wifi_ssid)

    @patch("zxdeck.frontends.touch.device_controller.connect_wifi")
    @patch("zxdeck.frontends.touch.device_controller.scan_wifi_networks")
    def test_wifi_password_connects_selected_network(self, scan, connect) -> None:
        scan.return_value = (WifiNetwork("Home", 80, "WPA2"),)
        connect.return_value = (True, "CONNECTED")
        controller = DeviceTouchUIController(())
        controller.handle_action("settings")
        controller.handle_action("wifi")
        controller.handle_action("select-wifi:0")
        controller.editor.text = "secret"

        controller.handle_action("wifi-connect")

        connect.assert_called_once_with("Home", "secret")
        self.assertEqual(WIFI_NETWORKS_SCREEN, controller.screen)
        self.assertEqual("CONNECTED Home", controller.wifi_status)

    @patch("zxdeck.frontends.touch.device_controller.connect_wifi")
    @patch("zxdeck.frontends.touch.device_controller.scan_wifi_networks")
    def test_open_wifi_connects_without_password(self, scan, connect) -> None:
        scan.return_value = (WifiNetwork("Guest", 50, "--"),)
        connect.return_value = (True, "CONNECTED")
        controller = DeviceTouchUIController(())
        controller.handle_action("settings")
        controller.handle_action("wifi")

        controller.handle_action("select-wifi:0")

        connect.assert_called_once_with("Guest", "")
        self.assertEqual(WIFI_NETWORKS_SCREEN, controller.screen)


if __name__ == "__main__":
    unittest.main()
