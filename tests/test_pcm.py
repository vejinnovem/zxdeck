from __future__ import annotations

from io import BytesIO
import unittest

from zxdeck.audio.pcm import count_pcm_samples, write_pcm
from zxdeck.tape.pulses import EncodedData, Pause, Pulse, PulseRun, ZX_CLOCK_HZ


class PcmTests(unittest.TestCase):
    def test_count_pcm_samples_matches_simple_timing(self) -> None:
        events = (PulseRun(3500, 2), Pause(1000))
        self.assertEqual(1002, count_pcm_samples(events, sample_rate=1000))

    def test_output_level_scales_signal_around_u8_silence(self) -> None:
        full = BytesIO()
        quiet = BytesIO()
        events = (Pulse(1), Pulse(1))
        write_pcm(events, full, sample_rate=ZX_CLOCK_HZ, chunk_size=1, level_percent=100)
        write_pcm(events, quiet, sample_rate=ZX_CLOCK_HZ, chunk_size=1, level_percent=25)

        self.assertEqual(bytes((32, 224)), full.getvalue())
        self.assertEqual(bytes((104, 152)), quiet.getvalue())

    def test_progress_reports_written_samples(self) -> None:
        output = BytesIO()
        progress = []
        total = write_pcm(
            (PulseRun(1, 3),),
            output,
            sample_rate=ZX_CLOCK_HZ,
            chunk_size=2,
            progress=progress.append,
        )
        self.assertEqual(3, total)
        self.assertEqual([2, 3], progress)

    def test_phase_progress_distinguishes_pilot_data_and_pause(self) -> None:
        output = BytesIO()
        phases = []
        write_pcm(
            (
                Pulse(3500),
                EncodedData(b"\x00", zero_tstates=3500, one_tstates=3500),
                Pause(1),
            ),
            output,
            sample_rate=1000,
            chunk_size=1,
            phase_progress=lambda _samples, phase: phases.append(phase),
        )

        self.assertEqual("pilot", phases[0])
        self.assertIn("data", phases)
        self.assertEqual("pause", phases[-1])


if __name__ == "__main__":
    unittest.main()
