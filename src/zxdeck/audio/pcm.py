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


def write_pcm(
    events: Iterable[TapeEvent],
    output: BinaryIO,
    *,
    sample_rate: int = 44_100,
    cancelled: Callable[[], bool] = lambda: False,
    chunk_size: int = 32_768,
) -> int:
    """Write PCM incrementally and return its total sample count."""
    if sample_rate <= 0:
        raise ValueError("sample rate must be positive")
    buffer = bytearray()
    level = False
    fraction = 0
    total = 0

    def samples_for_tstates(tstates: int) -> int:
        nonlocal fraction
        scaled = tstates * sample_rate + fraction
        count, fraction = divmod(scaled, ZX_CLOCK_HZ)
        return count

    def append(value: int, count: int) -> None:
        nonlocal total
        while count:
            room = chunk_size - len(buffer)
            take = min(count, room)
            buffer.extend(bytes((value,)) * take)
            count -= take
            total += take
            if len(buffer) >= chunk_size:
                output.write(buffer)
                buffer.clear()

    for event in events:
        if cancelled():
            break
        if isinstance(event, (Pulse, PulseRun)):
            count = event.count if isinstance(event, PulseRun) else 1
            for pulse_index in range(count):
                if pulse_index % 256 == 0 and cancelled():
                    return total
                append(224 if level else 32, samples_for_tstates(event.tstates))
                level = not level
        elif isinstance(event, EncodedData):
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
                        append(224 if level else 32, samples_for_tstates(duration))
                        level = not level
        elif isinstance(event, Pause):
            fraction = 0
            append(128, round(event.milliseconds * sample_rate / 1000))
            level = False
        elif isinstance(event, DirectRecording):
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
                    append(
                        224 if level else 32,
                        samples_for_tstates(event.tstates_per_sample),
                    )
    if buffer:
        output.write(buffer)
    return total
