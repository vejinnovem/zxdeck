"""Device-specific controller actions for ALSA mixer and Wi-Fi setup."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from zxdeck.audio import hardware_output_state, set_hardware_output_level
from zxdeck.system import WifiNetwork, connect_wifi, scan_wifi_networks

from .controller import TouchUIController as BaseTouchUIController
from .keypad import MultiTapEditor
from .renderer import RenderedScreen, Screen, TouchRenderer


WIFI_NETWORKS_SCREEN = "wifi-networks"
WIFI_PASSWORD_SCREEN = "wifi-password"


@dataclass(slots=True)
class DeviceTouchUIController(BaseTouchUIController):
    """Add operating-system controls while keeping the base controller testable."""

    settings_entry_count: int = 8
    output_level_mode: str = "tape"
    previous_hardware_output_level: int = 100
    wifi_networks: Sequence[WifiNetwork] = ()
    wifi_offset: int = 0
    visible_wifi_count: int = 5
    wifi_status: str = "NOT SCANNED"
    pending_wifi_ssid: str = ""

    def render(
        self,
        renderer: TouchRenderer,
        *,
        cursor_visible: bool = True,
    ) -> RenderedScreen:
        if (
            self.screen is Screen.OUTPUT_LEVEL
            and self.output_level_mode == "hardware"
        ):
            return renderer.render_hardware_output_level(
                self.selected_playback_device
            )
        if self.screen == WIFI_NETWORKS_SCREEN:
            return renderer.render_wifi_networks(
                self.wifi_networks,
                offset=self.wifi_offset,
                status=self.wifi_status,
            )
        if self.screen == WIFI_PASSWORD_SCREEN:
            return renderer.render_wifi_password(
                self.editor,
                self.pending_wifi_ssid,
                cursor_visible=cursor_visible,
            )
        # dataclass(slots=True) returns a replacement class object. Using
        # zero-argument super() in that replacement can retain the original
        # class in the __class__ closure and raise TypeError at runtime.
        return BaseTouchUIController.render(
            self,
            renderer,
            cursor_visible=cursor_visible,
        )

    def handle_action(self, action: str) -> None:
        if self.screen == WIFI_NETWORKS_SCREEN:
            self._handle_wifi_networks(action)
            return
        if self.screen == WIFI_PASSWORD_SCREEN:
            self._handle_wifi_password(action)
            return
        BaseTouchUIController.handle_action(self, action)

    def _handle_home(self, action: str) -> None:
        if action == "record":
            self._stop_transport()
            self.state = self.state.next_revision(error="REC NOT IMPLEMENTED")
            return
        BaseTouchUIController._handle_home(self, action)

    def _handle_settings(self, action: str) -> None:
        if action == "output-level":
            self.output_level_mode = "tape"
            BaseTouchUIController._handle_settings(self, action)
        elif action == "hardware-output":
            self.output_level_mode = "hardware"
            state = hardware_output_state(self.selected_playback_device)
            if state is not None and state.level > 0:
                self.previous_hardware_output_level = state.level
            self.screen = Screen.OUTPUT_LEVEL
        elif action == "wifi":
            self._refresh_wifi(rescan=True)
            self.screen = WIFI_NETWORKS_SCREEN
        else:
            BaseTouchUIController._handle_settings(self, action)

    def _handle_output_level(self, action: str) -> None:
        if self.output_level_mode != "hardware":
            BaseTouchUIController._handle_output_level(self, action)
            return
        if action == "back":
            self.screen = Screen.SETTINGS
            return

        state = hardware_output_state(self.selected_playback_device)
        if state is None:
            return
        if action == "volume-down":
            target = state.level - 5
        elif action == "volume-up":
            target = state.level + 5
        elif action == "volume-mute":
            if state.level > 0:
                self.previous_hardware_output_level = state.level
                target = 0
            else:
                target = max(5, self.previous_hardware_output_level)
        else:
            return

        changed = set_hardware_output_level(
            self.selected_playback_device,
            target,
        )
        if changed is not None and changed.level > 0:
            self.previous_hardware_output_level = changed.level

    def _refresh_wifi(self, *, rescan: bool) -> None:
        networks = scan_wifi_networks(rescan=rescan)
        self.wifi_networks = networks
        self.wifi_offset = min(
            self.wifi_offset,
            max(0, len(networks) - self.visible_wifi_count),
        )
        active = next(
            (network.ssid for network in networks if network.active),
            None,
        )
        if active:
            self.wifi_status = f"CONNECTED {active}"
        elif networks:
            self.wifi_status = f"{len(networks)} NETWORKS"
        else:
            self.wifi_status = "NO NETWORKS"

    def _handle_wifi_networks(self, action: str) -> None:
        if action == "back":
            self.screen = Screen.SETTINGS
            return
        if action == "wifi-up":
            self.wifi_offset = max(0, self.wifi_offset - 1)
            return
        if action == "wifi-down":
            self.wifi_offset = min(
                max(0, len(self.wifi_networks) - self.visible_wifi_count),
                self.wifi_offset + 1,
            )
            return
        if action == "wifi-rescan":
            self._refresh_wifi(rescan=True)
            return
        if not action.startswith("select-wifi:"):
            return

        try:
            index = int(action.split(":", 1)[1])
            network = self.wifi_networks[index]
        except (ValueError, IndexError):
            return

        self.pending_wifi_ssid = network.ssid
        self.editor = MultiTapEditor(max_length=63)
        if network.secured:
            self.screen = WIFI_PASSWORD_SCREEN
        else:
            self._connect_selected_wifi("")

    def _handle_wifi_password(self, action: str) -> None:
        if action == "cancel":
            self.screen = WIFI_NETWORKS_SCREEN
        elif action == "wifi-connect":
            self.editor.commit_pending()
            self._connect_selected_wifi(self.editor.text)
        elif action.startswith("key:"):
            self.editor.press(action.split(":", 1)[1])

    def _connect_selected_wifi(self, password: str) -> None:
        ssid = self.pending_wifi_ssid.strip()
        if not ssid:
            self.wifi_status = "NO SSID SELECTED"
            self.screen = WIFI_NETWORKS_SCREEN
            return

        connected, detail = connect_wifi(ssid, password)
        self._refresh_wifi(rescan=False)
        if connected:
            self.wifi_status = f"CONNECTED {ssid}"
        else:
            self.wifi_status = (
                ("FAILED " + detail).upper()[:32]
                if detail
                else "CONNECTION FAILED"
            )
        self.screen = WIFI_NETWORKS_SCREEN
