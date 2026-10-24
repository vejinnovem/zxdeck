"""Convert tape signal events to unsigned 8-bit mono PCM."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import BinaryIO

from zxdeck.tape.pulses import (
    DirectRecording,
    EncodedData,
    Pause,
    Pulse,
    PulseRun,
    TapeEvent,
    ZX_CLOCK_HZ,
)


LevelSource = int | Callable[[], int]
PhaseProgress = Callable[[int, str], None]


def count_pcm_samples(
    events: Iterable[TapeEvent],
    *,
    sample_rate: int = 44_100,
) -> int:
    """Return the exact PCM sample count without generating the PCM bytes."""
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")

    total = 0
    fraction = 0

    def add_tstates(tstates: int) -> None:
        nonlocal total, fraction
        scaled = tstates * sample_rate + fraction
        count, fraction = divmod(scaled, ZX_CLOCK_HZ)
        total += count

    for event in events:
        if isinstance(event, Pulse):
            add_tstates(event.tstates)
        elif isinstance(event, PulseRun):
            add_tstates(event.tstates * event.count)
        elif isinstance(event, EncodedData):
            if not 1 <= event.used_bits_last_byte <= 8:
                raise ValueError("invalid encoded-data used-bit count")
            if not event.data:
                continue
            full = event.data[:-1]
            last = event.data[-1]
            total_bits = len(full) * 8 + event.used_bits_last_byte
            ones = sum(value.bit_count() for value in full)
            mask = 0xFF & (0xFF << (8 - event.used_bits_last_byte))
            ones += (last & mask).bit_count()
            zeros = total_bits - ones
            add_tstates(
                2
                * (
                    zeros * event.zero_tstates
                    + ones * event.one_tstates
                )
            )
        elif isinstance(event, Pause):
            fraction = 0
            total += round(event.milliseconds * sample_rate / 1000)
        elif isinstance(event, DirectRecording):
            if not 1 <= event.used_bits_last_byte <= 8:
                raise ValueError("invalid direct-recording used-bit count")
            if not event.data:
                continue
            total_bits = (len(event.data) - 1) * 8 + event.used_bits_last_byte
            add_tstates(total_bits * event.tstates_per_sample)

    return total


def write_pcm(
    events: Iterable[TapeEvent],
    output: BinaryIO,
    *,
    sample_rate: int = 44_100,
    cancelled: Callable[[], bool] = lambda: False,
    chunk_size: int = 32_768,
    level_percent: LevelSource = 100,
    progress: Callable[[int], None] | None = None,
    phase_progress: PhaseProgress | None = None,
) -> int:
    """Write PCM incrementally and return its total sample count.

    ``phase_progress`` reports both regular flushed progress and exact logical
    signal boundaries. Pulse/pulse-run sections are ``pilot`` (including sync
    pulses), encoded/direct data are ``data`` and silence blocks are ``pause``.

    A phase transition first flushes any samples belonging to the previous
    phase, then reports the new phase at the exact sample offset where it
    begins. This keeps UI pilot/data stripes from lagging by up to one complete
    PCM chunk or attributing a mixed chunk to the wrong phase.
    """
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    if chunk_size <= 0:
        raise ValueError("chunk size must be positive")

    buffer = bytearray()
    level = False
    fraction = 0
    total = 0
    low_value = 32
    high_value = 224
    current_phase: str | None = None

    def refresh_signal_levels() -> None:
        nonlocal low_value, high_value
        raw = level_percent() if callable(level_percent) else level_percent
        percent = max(0, min(100, int(raw)))
        amplitude = round(96 * percent / 100)
        low_value = 128 - amplitude
        high_value = 128 + amplitude

    def samples_for_tstates(tstates: int) -> int:
        nonlocal fraction
        scaled = tstates * sample_rate + fraction
        count, fraction = divmod(scaled, ZX_CLOCK_HZ)
        return count

    def flush() -> None:
        if not buffer:
            return
        output.write(buffer)
        buffer.clear()
        if progress is not None:
            progress(total)
        if phase_progress is not None and current_phase is not None:
            phase_progress(total, current_phase)
        refresh_signal_levels()

    def set_phase(phase: str) -> None:
        nonlocal current_phase
        if phase == current_phase:
            return
        # Never let a buffer span two logical phases. Otherwise the callback
        # only discovers the new phase after enough new samples arrive to fill
        # the chunk, which can delay a UI transition by one full chunk.
        if current_phase is not None:
            flush()
        current_phase = phase
        if phase_progress is not None:
            phase_progress(total, current_phase)

    def append_constant(value: int, count: int) -> None:
        nonlocal total
        while count:
            room = chunk_size - len(buffer)
            take = min(count, room)
            buffer.extend(bytes((value,)) * take)
            count -= take
            total += take
            if len(buffer) >= chunk_size:
                flush()

    def append_signal(is_high: bool, count: int) -> None:
        nonlocal total
        while count:
            room = chunk_size - len(buffer)
            take = min(count, room)
            value = high_value if is_high else low_value
            buffer.extend(bytes((value,)) * take)
            count -= take
            total += take
            if len(buffer) >= chunk_size:
                flush()

    refresh_signal_levels()

    for event in events:
        if cancelled():
            break
        if isinstance(event, (Pulse, PulseRun)):
            set_phase("pilot")
            count = event.count if isinstance(event, PulseRun) else 1
            for pulse_index in range(count):
                if pulse_index % 256 == 0 and cancelled():
                    return total
                append_signal(level, samples_for_tstates(event.tstates))
                level = not level
        elif isinstance(event, EncodedData):
            set_phase("data")
            if not 1 <= event.used_bits_last_byte <= 8:
                raise ValueError("invalid encoded-data used-bit count")
            for byte_index, value in enumerate(event.data):
                if cancelled():
                    return total
                bit_count = (
                    event.used_bits_last_byte
                    if byte_index == len(event.data) - 1
                    else 8
                )
                for shift in range(7, 7 - bit_count, -1):
                    duration = (
                        event.one_tstates
                        if value & (1 << shift)
                        else event.zero_tstates
                    )
                    for _ in range(2):
                        append_signal(level, samples_for_tstates(duration))
                        level = not level
        elif isinstance(event, Pause):
            set_phase("pause")
            fraction = 0
            append_constant(128, round(event.milliseconds * sample_rate / 1000))
            level = False
        elif isinstance(event, DirectRecording):
            set_phase("data")
            if not 1 <= event.used_bits_last_byte <= 8:
                raise ValueError("invalid direct-recording used-bit count")
            for byte_index, value in enumerate(event.data):
                if cancelled():
                    return total
                bit_count = (
                    event.used_bits_last_byte
                    if byte_index == len(event.data) - 1
                    else 8
                )
                for shift in range(7, 7 - bit_count, -1):
                    level = bool(value & (1 << shift))
                    append_signal(
                        level,
                        samples_for_tstates(event.tstates_per_sample),
                    )
    if buffer:
        flush()
    return total
