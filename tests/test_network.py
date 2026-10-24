from __future__ import annotations

import unittest

from zxdeck.system.network import parse_ipv4_addresses, parse_nmcli_wifi


class NetworkTests(unittest.TestCase):
    def test_parse_ipv4_addresses_filters_ipv6_loopback_and_duplicates(self) -> None:
        addresses = parse_ipv4_addresses(
            "192.168.1.84 127.0.0.1 fe80::1234 10.0.0.7 192.168.1.84\n"
        )

        self.assertEqual(("192.168.1.84", "10.0.0.7"), addresses)

    def test_parse_ipv4_addresses_handles_empty_or_invalid_output(self) -> None:
        self.assertEqual((), parse_ipv4_addresses(""))
        self.assertEqual((), parse_ipv4_addresses("not-an-address ::1"))

    def test_parse_nmcli_wifi_sorts_active_then_signal_and_unescapes_colon(self) -> None:
        networks = parse_nmcli_wifi(
            ":Guest:35:--\n"
            "*:Home\\:Lab:72:WPA2\n"
            ":Home\\:Lab:55:WPA2\n"
            ":Strong:90:WPA3\n"
        )

        self.assertEqual(
            ("Home:Lab", "Strong", "Guest"),
            tuple(network.ssid for network in networks),
        )
        self.assertTrue(networks[0].active)
        self.assertTrue(networks[0].secured)
        self.assertFalse(networks[2].secured)


if __name__ == "__main__":
    unittest.main()
