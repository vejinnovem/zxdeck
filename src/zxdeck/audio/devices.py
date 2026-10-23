"""Discover physical ALSA playback and capture endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
import subprocess
from typing import Literal


@dataclass(frozen=True, slots=True)
class AudioDevice:
    name: str
    alsa_name: str


_DEVICE_LINE = re.compile(
    r"^card\s+\d+:\s+(?P<card>\S+)\s+\[(?P<card_label>[^]]+)\],\s+"
    r"device\s+(?P<device>\d+):\s+(?P<device_label>.+?)\s+\["
)


def list_audio_devices(
    direction: Literal["playback", "capture"],
) -> tuple[AudioDevice, ...]:
    command = "aplay" if direction == "playback" else "arecord"
    environment = dict(os.environ)
    environment["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            (command, "-l"),
            capture_output=True,
            text=True,
            timeout=3,
            env=environment,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ()

    devices = []
    for line in result.stdout.splitlines():
        match = _DEVICE_LINE.match(line)
        if match is None:
            continue
        card = match.group("card")
        device = match.group("device")
        label = match.group("card_label").strip()
        device_label = match.group("device_label").strip()
        devices.append(
            AudioDevice(
                f"{label}: {device_label}",
                f"plughw:CARD={card},DEV={device}",
            )
        )
    return tuple(devices)
