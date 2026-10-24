from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from tools.boot_splash import notify_systemd_ready


class BootSplashTests(unittest.TestCase):
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
