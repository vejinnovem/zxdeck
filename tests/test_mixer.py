from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from zxdeck.audio.mixer import (
    hardware_output_state,
    mixer_device_for_playback,
    set_hardware_output_level,
)


class HardwareMixerTests(unittest.TestCase):
    def test_playback_pcm_maps_to_control_device(self) -> None:
        self.assertEqual(
            "hw:CARD=Device",
            mixer_device_for_playback("plughw:CARD=Device,DEV=0"),
        )
        self.assertEqual(
            "hw:2",
            mixer_device_for_playback("hw:2,0"),
        )
        self.assertIsNone(mixer_device_for_playback("default"))

    @patch("zxdeck.audio.mixer.subprocess.run")
    def test_reads_preferred_speaker_playback_level(self, run) -> None:
        run.side_effect = (
            subprocess.CompletedProcess(
                ("amixer",),
                0,
                stdout=(
                    "Simple mixer control 'Mic',0\n"
                    "Simple mixer control 'Speaker',0\n"
                ),
                stderr="",
            ),
            subprocess.CompletedProcess(
                ("amixer",),
                0,
                stdout=(
                    "Front Left: Playback 32 [50%] [on]\n"
                    "Front Right: Playback 32 [50%] [on]\n"
                ),
                stderr="",
            ),
        )

        state = hardware_output_state("plughw:CARD=Device,DEV=0")

        self.assertIsNotNone(state)
        self.assertEqual("Speaker", state.control_name)
        self.assertEqual(50, state.level)

    @patch("zxdeck.audio.mixer.subprocess.run")
    def test_sets_hardware_level_and_reads_back(self, run) -> None:
        controls = subprocess.CompletedProcess(
            ("amixer",),
            0,
            stdout="Simple mixer control 'Speaker',0\n",
            stderr="",
        )
        at_50 = subprocess.CompletedProcess(
            ("amixer",),
            0,
            stdout="Front Left: Playback 32 [50%] [on]\n",
            stderr="",
        )
        set_ok = subprocess.CompletedProcess(("amixer",), 0, stdout="", stderr="")
        at_100 = subprocess.CompletedProcess(
            ("amixer",),
            0,
            stdout="Front Left: Playback 64 [100%] [on]\n",
            stderr="",
        )
        run.side_effect = (controls, at_50, set_ok, at_100)

        state = set_hardware_output_level(
            "plughw:CARD=Device,DEV=0",
            100,
        )

        self.assertIsNotNone(state)
        self.assertEqual(100, state.level)


if __name__ == "__main__":
    unittest.main()
