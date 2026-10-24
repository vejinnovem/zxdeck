from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from zxdeck.audio.pcm import write_pcm
from zxdeck.tape.pulses import (
    DirectRecording,
    EncodedData,
    Pause,
    Pulse,
    PulseRun,
    TapeDecodeError,
    TapeStop,
    iter_tape_events,
)


class TapePulseTests(unittest.TestCase):
    def test_tap_header_uses_standard_pilot_and_pause(self) -> None:
        block = bytes((0x00, 0x00))
        image = len(block).to_bytes(2, "little") + block
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "header.tap"
            path.write_bytes(image)
            events = list(iter_tape_events(path))

        self.assertEqual(PulseRun(2168, 8063), events[0])
        self.assertEqual(Pulse(667), events[1])
        self.assertEqual(Pulse(735), events[2])
        self.assertEqual(EncodedData(block, 855, 1710), events[3])
        self.assertEqual(Pause(1000), events[-1])
        self.assertEqual(5, len(events))

    def test_tzx_turbo_and_direct_recording_are_decoded(self) -> None:
        turbo_header = (
            (100).to_bytes(2, "little")
            + (101).to_bytes(2, "little")
            + (102).to_bytes(2, "little")
            + (103).to_bytes(2, "little")
            + (104).to_bytes(2, "little")
            + (2).to_bytes(2, "little")
            + bytes((1,))
            + (20).to_bytes(2, "little")
            + (1).to_bytes(3, "little")
        )
        direct_header = (
            (79).to_bytes(2, "little")
            + (10).to_bytes(2, "little")
            + bytes((2,))
            + (1).to_bytes(3, "little")
        )
        image = (
            b"ZXTape!\x1a\x01\x14"
            + b"\x11"
            + turbo_header
            + b"\x80"
            + b"\x15"
            + direct_header
            + b"\x80"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "turbo.tzx"
            path.write_bytes(image)
            events = list(iter_tape_events(path))

        self.assertEqual(PulseRun(100, 2), events[0])
        self.assertEqual(Pulse(101), events[1])
        self.assertEqual(Pulse(102), events[2])
        self.assertEqual(EncodedData(b"\x80", 103, 104, 1), events[3])
        self.assertEqual(Pause(20), events[4])
        self.assertEqual(DirectRecording(79, b"\x80", 2), events[5])
        self.assertEqual(Pause(10), events[6])

    def test_generalized_tzx_fails_explicitly(self) -> None:
        image = b"ZXTape!\x1a\x01\x14\x19\x00\x00\x00\x00"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "generalized.tzx"
            path.write_bytes(image)
            with self.assertRaisesRegex(TapeDecodeError, "0x19"):
                list(iter_tape_events(path))

    def test_zero_data_pause_means_no_pause_but_zero_pause_block_stops(self) -> None:
        standard = b"\x10\x00\x00\x01\x00\xff"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "no-pause.tzx"
            path.write_bytes(b"ZXTape!\x1a\x01\x14" + standard)
            self.assertNotIsInstance(list(iter_tape_events(path))[-1], Pause)

            path.write_bytes(b"ZXTape!\x1a\x01\x14\x20\x00\x00")
            self.assertEqual([TapeStop()], list(iter_tape_events(path)))

    def test_pcm_preserves_fractional_timing_and_pause(self) -> None:
        output = BytesIO()
        count = write_pcm(
            [Pulse(1750000), Pulse(1750000), Pause(100)],
            output,
            sample_rate=100,
        )
        self.assertEqual(110, count)
        self.assertEqual(bytes((32,)) * 50, output.getvalue()[:50])
        self.assertEqual(bytes((224,)) * 50, output.getvalue()[50:100])
        self.assertEqual(bytes((128,)) * 10, output.getvalue()[100:])

    def test_pcm_generation_can_be_cancelled_inside_a_long_run(self) -> None:
        output = BytesIO()
        checks = 0

        def cancelled() -> bool:
            nonlocal checks
            checks += 1
            return checks > 1

        count = write_pcm(
            [PulseRun(2168, 8063)],
            output,
            cancelled=cancelled,
        )
        self.assertLess(count, 8063 * 28)


if __name__ == "__main__":
    unittest.main()
