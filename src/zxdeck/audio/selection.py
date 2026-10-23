"""Persist ALSA choices outside the checkout."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AudioSelection:
    playback_device: str
    capture_device: str


def load_audio_selection(
    state_file: Path,
    *,
    default_playback: str,
    default_capture: str,
) -> AudioSelection:
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return AudioSelection(default_playback, default_capture)
    playback = data.get("playback_device", default_playback)
    capture = data.get("capture_device", default_capture)
    if not isinstance(playback, str) or not isinstance(capture, str):
        return AudioSelection(default_playback, default_capture)
    return AudioSelection(playback, capture)


def save_audio_selection(state_file: Path, selection: AudioSelection) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_file.with_suffix(state_file.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {
                "playback_device": selection.playback_device,
                "capture_device": selection.capture_device,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(state_file)
