"""Persist ALSA choices and the software output level outside the checkout."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


DEFAULT_OUTPUT_LEVEL = 25


@dataclass(frozen=True, slots=True)
class AudioSelection:
    playback_device: str
    capture_device: str
    output_level: int = DEFAULT_OUTPUT_LEVEL


def load_audio_selection(
    state_file: Path,
    *,
    default_playback: str,
    default_capture: str,
    default_output_level: int = DEFAULT_OUTPUT_LEVEL,
) -> AudioSelection:
    default_output_level = max(0, min(100, int(default_output_level)))
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return AudioSelection(default_playback, default_capture, default_output_level)
    playback = data.get("playback_device", default_playback)
    capture = data.get("capture_device", default_capture)
    output_level = data.get("output_level", default_output_level)
    if not isinstance(playback, str) or not isinstance(capture, str):
        return AudioSelection(default_playback, default_capture, default_output_level)
    if isinstance(output_level, bool) or not isinstance(output_level, int):
        output_level = default_output_level
    output_level = max(0, min(100, output_level))
    return AudioSelection(playback, capture, output_level)


def save_audio_selection(state_file: Path, selection: AudioSelection) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_file.with_suffix(state_file.suffix + ".tmp")
    temporary.write_text(
        json.dumps(
            {
                "playback_device": selection.playback_device,
                "capture_device": selection.capture_device,
                "output_level": max(0, min(100, int(selection.output_level))),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(state_file)
