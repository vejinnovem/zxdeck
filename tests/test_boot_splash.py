from __future__ import annotations

import os
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from tools.boot_splash import notify_systemd_ready, wait_for_devices


class BootSplashTests(unittest.TestCase):
    def test_device_wait_checks_access_instead_of_only_existence(self) -> None:
        config = SimpleNamespace(spi_bus=0, spi_device=0)
        descriptors = iter((PermissionError("udev pending"), 10, 11, 12))

        def open_device(_path, _flags):
            result = next(descriptors)
            if isinstance(result, OSError):
                raise result
            return result

        with patch("tools.boot_splash.os.open", side_effect=open_device):
            with patch("tools.boot_splash.os.close") as close:
                with patch("tools.boot_splash.time.monotonic", side_effect=(0.0, 0.1)):
                    with patch("tools.boot_splash.time.sleep"):
                        wait_for_devices(config, 1.0)

        self.assertEqual(close.call_count, 3)

    def test_ready_notification_is_optional_outside_systemd(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            notify_systemd_ready()

    def test_ready_notification_reaches_systemd_socket(self) -> None:
        notifier = MagicMock()
        notifier.__enter__.return_value = notifier
        with patch("tools.boot_splash.socket.socket", return_value=notifier):
            with patch.dict(os.environ, {"NOTIFY_SOCKET": "/run/notify.sock"}):
                notify_systemd_ready()
        notifier.connect.assert_called_once_with("/run/notify.sock")
        notifier.sendall.assert_called_once_with(b"READY=1")

    def test_abstract_systemd_socket_is_converted_for_python(self) -> None:
        notifier = MagicMock()
        notifier.__enter__.return_value = notifier
        with patch("tools.boot_splash.socket.socket", return_value=notifier):
            with patch.dict(os.environ, {"NOTIFY_SOCKET": "@abstract"}):
                notify_systemd_ready()
        notifier.connect.assert_called_once_with("\0abstract")


if __name__ == "__main__":
    unittest.main()
