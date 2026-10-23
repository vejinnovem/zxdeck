from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from zxdeck.audio import (
    AudioSelection,
    list_audio_devices,
    load_audio_selection,
    save_audio_selection,
)


class AudioDeviceTests(unittest.TestCase):
    @patch("zxdeck.audio.devices.subprocess.run")
    def test_physical_alsa_devices_use_stable_card_names(self, run) -> None:
        run.return_value = subprocess.CompletedProcess(
            ("aplay", "-l"),
            0,
            stdout=(
                "**** List of PLAYBACK Hardware Devices ****\n"
                "card 2: Device [USB Audio Device], device 0: USB Audio [USB Audio]\n"
            ),
            stderr="",
        )

        devices = list_audio_devices("playback")

        self.assertEqual("USB Audio Device: USB Audio", devices[0].name)
        self.assertEqual("plughw:CARD=Device,DEV=0", devices[0].alsa_name)
        self.assertEqual("aplay", run.call_args.args[0][0])

    @patch("zxdeck.audio.devices.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_alsa_tools_produce_an_empty_list(self, _run) -> None:
        self.assertEqual((), list_audio_devices("capture"))

    def test_audio_selection_round_trip_and_invalid_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state" / "audio.json"
            selection = AudioSelection("plughw:CARD=USB,DEV=0", "hw:USB,0")
            save_audio_selection(state, selection)
            self.assertEqual(
                selection,
                load_audio_selection(
                    state,
                    default_playback="default",
                    default_capture="default",
                ),
            )
            state.write_text("not json", encoding="utf-8")
            self.assertEqual(
                AudioSelection("default", "default"),
                load_audio_selection(
                    state,
                    default_playback="default",
                    default_capture="default",
                ),
            )
