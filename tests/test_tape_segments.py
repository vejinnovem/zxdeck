from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from zxdeck.tape import (
    inspect_tape_segments,
    select_tape_segment,
    selected_event_index,
)


class TapeSegmentTests(unittest.TestCase):
    def test_tap_header_and_data_become_named_segments(self) -> None:
        header = (
            b"\x00\x00"
            + b"RING      "
            + (2).to_bytes(2, "little")
            + (10).to_bytes(2, "little")
            + (0).to_bytes(2, "little")
            + b"\x00"
        )
        data = b"\xff\x00"
        image = (
            len(header).to_bytes(2, "little")
            + header
            + len(data).to_bytes(2, "little")
            + data
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.tap"
            path.write_bytes(image)
            segments = inspect_tape_segments(path)

            self.assertEqual(2, len(segments))
            self.assertEqual("PROGRAM RING", segments[0].label)
            self.assertEqual("DATA RING", segments[1].label)
            self.assertEqual(0, segments[0].event_index)
            self.assertGreater(segments[1].event_index, segments[0].event_index)
            self.assertGreater(segments[1].start_seconds, segments[0].start_seconds)

            select_tape_segment(path, segments[1].event_index)
            self.assertEqual(
                segments[1].event_index,
                selected_event_index(path),
            )

    def test_tzx_manual_stop_keeps_later_segment_navigable(self) -> None:
        first = b"\x10\xe8\x03\x02\x00\xff\x00"
        stop = b"\x20\x00\x00"
        second = b"\x10\xe8\x03\x02\x00\xff\x01"
        image = b"ZXTape!\x1a\x01\x14" + first + stop + second

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "multi.tzx"
            path.write_bytes(image)
            segments = inspect_tape_segments(path)

        self.assertEqual(2, len(segments))
        self.assertEqual("DATA BLOCK 1", segments[0].label)
        self.assertEqual("DATA BLOCK 2", segments[1].label)
        self.assertGreater(segments[1].event_index, segments[0].event_index)


if __name__ == "__main__":
    unittest.main()
