"""Structural tape segment metadata used by the transport UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .pulses import (
    DirectRecording,
    EncodedData,
    Pause,
    Pulse,
    PulseRun,
    TapeEvent,
    TapeStop,
    ZX_CLOCK_HZ,
    iter_tape_events,
)


@dataclass(frozen=True, slots=True)
class TapeSegment:
    """One navigable signal section beginning at an event boundary."""

    index: int
    event_index: int
    start_seconds: float
    label: str


_selected_event_indices: dict[str, int] = {}


def select_tape_segment(path: str | Path, event_index: int) -> None:
    """Remember which event boundary should be used by the next playback."""
    _selected_event_indices[str(Path(path).resolve())] = max(0, int(event_index))


def selected_event_index(path: str | Path) -> int:
    """Return the event boundary selected for the next playback."""
    return _selected_event_indices.get(str(Path(path).resolve()), 0)


def inspect_tape_segments(path: str | Path) -> tuple[TapeSegment, ...]:
    """Return navigable signal starts without generating PCM audio.

    Standard/turbo data blocks begin with a PulseRun and become one segment.
    Pure-data and direct-recording blocks also become segments.  The function
    intentionally stays conservative: it marks useful transport boundaries,
    not every individual pulse.
    """
    events = tuple(iter_tape_events(path))
    segments: list[TapeSegment] = []
    elapsed = 0.0
    previous_header_name: str | None = None

    for event_index, event in enumerate(events):
        if _starts_segment(events, event_index):
            data_event = _segment_data_event(events, event_index)
            label, header_name, consumes_header_name = _segment_label(
                data_event,
                previous_header_name,
                len(segments) + 1,
                event,
            )
            if header_name is not None:
                previous_header_name = header_name
            elif consumes_header_name:
                previous_header_name = None
            segments.append(
                TapeSegment(
                    index=len(segments),
                    event_index=event_index,
                    start_seconds=elapsed,
                    label=label,
                )
            )
        elapsed += _event_duration_seconds(event)

    if not segments and events:
        segments.append(TapeSegment(0, 0, 0.0, "TAPE START"))
    return tuple(segments)


def _starts_segment(events: tuple[TapeEvent, ...], index: int) -> bool:
    event = events[index]
    if isinstance(event, PulseRun):
        return True
    if isinstance(event, (EncodedData, DirectRecording)):
        return index == 0 or not isinstance(events[index - 1], (Pulse, PulseRun))
    if isinstance(event, Pulse):
        return index == 0 or isinstance(events[index - 1], (Pause, TapeStop))
    return False


def _segment_data_event(
    events: tuple[TapeEvent, ...],
    start: int,
) -> EncodedData | DirectRecording | None:
    for event in events[start : start + 5]:
        if isinstance(event, (EncodedData, DirectRecording)):
            return event
        if isinstance(event, (Pause, TapeStop)):
            break
    return None


def _segment_label(
    data_event: EncodedData | DirectRecording | None,
    previous_header_name: str | None,
    number: int,
    first_event: TapeEvent,
) -> tuple[str, str | None, bool]:
    if isinstance(data_event, EncodedData):
        header = _spectrum_header(data_event.data)
        if header is not None:
            kind, name = header
            return f"{kind} {name}".strip(), name, False
        if previous_header_name:
            return f"DATA {previous_header_name}", None, True
        return f"DATA BLOCK {number}", None, False
    if isinstance(data_event, DirectRecording):
        return f"DIRECT BLOCK {number}", None, False
    if isinstance(first_event, PulseRun):
        return f"PILOT {number}", None, False
    return f"SEGMENT {number}", None, False


def _spectrum_header(data: bytes) -> tuple[str, str] | None:
    # Standard Spectrum header block: flag + 17-byte header + checksum.
    if len(data) < 19 or data[0] != 0x00 or data[1] > 3:
        return None
    kinds = ("PROGRAM", "NUM ARRAY", "CHAR ARRAY", "CODE")
    raw_name = data[2:12]
    name = raw_name.decode("ascii", errors="replace").strip().replace("\x00", "")
    return kinds[data[1]], name or "UNNAMED"


def _event_duration_seconds(event: TapeEvent) -> float:
    if isinstance(event, Pulse):
        return event.tstates / ZX_CLOCK_HZ
    if isinstance(event, PulseRun):
        return event.tstates * event.count / ZX_CLOCK_HZ
    if isinstance(event, EncodedData):
        if not event.data:
            return 0.0
        full = event.data[:-1]
        last = event.data[-1]
        total_bits = len(full) * 8 + event.used_bits_last_byte
        ones = sum(value.bit_count() for value in full)
        mask = 0xFF & (0xFF << (8 - event.used_bits_last_byte))
        ones += (last & mask).bit_count()
        zeros = total_bits - ones
        tstates = 2 * (
            zeros * event.zero_tstates + ones * event.one_tstates
        )
        return tstates / ZX_CLOCK_HZ
    if isinstance(event, Pause):
        return event.milliseconds / 1000.0
    if isinstance(event, DirectRecording):
        if not event.data:
            return 0.0
        total_bits = (len(event.data) - 1) * 8 + event.used_bits_last_byte
        return total_bits * event.tstates_per_sample / ZX_CLOCK_HZ
    return 0.0
