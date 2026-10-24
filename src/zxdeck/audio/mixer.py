"""Read and adjust the hardware playback mixer behind an ALSA device."""

from __future__ import annotations

from dataclasses import dataclass
import re
import subprocess


_CONTROL_RE = re.compile(r"Simple mixer control '(.+)',\d+")
_PLAYBACK_PERCENT_RE = re.compile(r"Playback.*?\[(\d+)%\]")
_CARD_RE = re.compile(r"(?:^|[,=:])CARD=([^,]+)", re.IGNORECASE)
_HW_INDEX_RE = re.compile(r"^(?:plug)?hw:(\d+)(?:,|$)", re.IGNORECASE)
_CONTROL_PRIORITY = ("speaker", "headphone", "pcm", "master")


@dataclass(frozen=True, slots=True)
class HardwareOutputState:
    mixer_device: str
    control_name: str
    level: int


def mixer_device_for_playback(playback_device: str) -> str | None:
    """Translate a playback PCM name into the corresponding ALSA control device."""
    match = _CARD_RE.search(playback_device)
    if match:
        return f"hw:CARD={match.group(1)}"
    match = _HW_INDEX_RE.match(playback_device)
    if match:
        return f"hw:{match.group(1)}"
    return None


def _amixer(
    mixer_device: str,
    *args: str,
    timeout: float = 2.0,
) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ("amixer", "-D", mixer_device, *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def _control_names(mixer_device: str) -> tuple[str, ...]:
    result = _amixer(mixer_device, "scontrols")
    if result is None or result.returncode != 0:
        return ()
    names = []
    for line in result.stdout.splitlines():
        match = _CONTROL_RE.search(line)
        if match and match.group(1) not in names:
            names.append(match.group(1))
    return tuple(names)


def _ordered_controls(names: tuple[str, ...]) -> tuple[str, ...]:
    def priority(name: str) -> tuple[int, str]:
        folded = name.casefold()
        for index, preferred in enumerate(_CONTROL_PRIORITY):
            if preferred in folded:
                return index, folded
        return len(_CONTROL_PRIORITY), folded

    return tuple(sorted(names, key=priority))


def _read_control_level(mixer_device: str, control_name: str) -> int | None:
    result = _amixer(mixer_device, "sget", control_name)
    if result is None or result.returncode != 0:
        return None
    levels = [
        int(value)
        for value in _PLAYBACK_PERCENT_RE.findall(result.stdout)
    ]
    if not levels:
        return None
    return max(0, min(100, round(sum(levels) / len(levels))))


def hardware_output_state(playback_device: str) -> HardwareOutputState | None:
    """Return the first usable playback-volume control for a PCM endpoint."""
    mixer_device = mixer_device_for_playback(playback_device)
    if mixer_device is None:
        return None
    for control_name in _ordered_controls(_control_names(mixer_device)):
        level = _read_control_level(mixer_device, control_name)
        if level is not None:
            return HardwareOutputState(mixer_device, control_name, level)
    return None


def set_hardware_output_level(
    playback_device: str,
    level: int,
) -> HardwareOutputState | None:
    """Set the selected card's playback mixer and return the resulting state."""
    current = hardware_output_state(playback_device)
    if current is None:
        return None
    level = max(0, min(100, int(level)))
    args = ("sset", current.control_name, f"{level}%")
    result = _amixer(current.mixer_device, *args, "unmute" if level else "mute")
    if result is None or result.returncode != 0:
        result = _amixer(current.mixer_device, *args)
    if result is None or result.returncode != 0:
        return None
    refreshed = _read_control_level(current.mixer_device, current.control_name)
    if refreshed is None:
        refreshed = level
    return HardwareOutputState(
        current.mixer_device,
        current.control_name,
        refreshed,
    )
