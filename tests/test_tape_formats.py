from __future__ import annotations

import unittest

from zxdeck.tape import probe_tape_bytes


def tap_block(payload: bytes) -> bytes:
    return len(payload).to_bytes(2, "little") + payload


class TapeFormatTests(unittest.TestCase):
    def test_valid_tap_blocks_and_checksum(self) -> None:
        probe = probe_tape_bytes(tap_block(bytes((0, 1, 2, 3))), ".tap")
        self.assertTrue(probe.strict)
        self.assertEqual("tap", probe.detected_format)
        self.assertEqual(1, probe.blocks)

    def test_bad_tap_checksum_is_warning_not_structural_failure(self) -> None:
        probe = probe_tape_bytes(tap_block(bytes((0, 1, 2))), ".tap")
        self.assertTrue(probe.valid)
        self.assertFalse(probe.strict)
        self.assertEqual(1, probe.checksum_failures)

    def test_truncated_tap_is_invalid(self) -> None:
        probe = probe_tape_bytes(b"\x10\x00short", ".tap")
        self.assertFalse(probe.valid)

    def test_tzx_header_and_mislabeled_tap_are_detected(self) -> None:
        tzx = probe_tape_bytes(b"ZXTape!\x1a\x01\x14", ".tzx")
        mislabeled = probe_tape_bytes(tap_block(bytes((0, 1, 2, 3))), ".tzx")
        self.assertTrue(tzx.strict)
        self.assertEqual("tzx", tzx.detected_format)
        self.assertTrue(mislabeled.strict)
        self.assertEqual(".tap", mislabeled.canonical_suffix)


if __name__ == "__main__":
    unittest.main()
