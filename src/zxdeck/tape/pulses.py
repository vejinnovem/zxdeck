"""Decode TAP and commonly used TZX blocks into tape signal events."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


ZX_CLOCK_HZ = 3_500_000


class TapeDecodeError(ValueError):
    """The image is truncated, malformed, or uses an unsupported tape block."""


@dataclass(frozen=True, slots=True)
class Pulse:
    tstates: int


@dataclass(frozen=True, slots=True)
class PulseRun:
    tstates: int
    count: int


@dataclass(frozen=True, slots=True)
class EncodedData:
    data: bytes
    zero_tstates: int
    one_tstates: int
    used_bits_last_byte: int = 8


@dataclass(frozen=True, slots=True)
class Pause:
    milliseconds: int


@dataclass(frozen=True, slots=True)
class DirectRecording:
    tstates_per_sample: int
    data: bytes
    used_bits_last_byte: int


TapeEvent = Pulse | PulseRun | EncodedData | Pause | DirectRecording


def iter_tape_events(path: str | Path) -> Iterator[TapeEvent]:
    tape_path = Path(path)
    data = tape_path.read_bytes()
    if data.startswith(b"ZXTape!\x1a"):
        yield from _iter_tzx(data)
    elif tape_path.suffix.casefold() == ".tap":
        yield from _iter_tap(data)
    else:
        raise TapeDecodeError(f"unsupported tape format: {tape_path.suffix}")


def _iter_tap(data: bytes) -> Iterator[TapeEvent]:
    position = 0
    blocks = 0
    while position < len(data):
        length, position = _number(data, position, 2)
        block, position = _take(data, position, length)
        if not block:
            raise TapeDecodeError("empty TAP block")
        yield from _data_block(block, pause_ms=1000)
        blocks += 1
    if not blocks:
        raise TapeDecodeError("TAP contains no blocks")


def _iter_tzx(data: bytes) -> Iterator[TapeEvent]:
    if len(data) < 10:
        raise TapeDecodeError("truncated TZX header")
    position = 10
    while position < len(data):
        block_id = data[position]
        position += 1

        if block_id == 0x10:
            header, position = _take(data, position, 4)
            pause_ms = int.from_bytes(header[0:2], "little")
            block, position = _take(
                data, position, int.from_bytes(header[2:4], "little")
            )
            yield from _data_block(block, pause_ms=pause_ms)
        elif block_id == 0x11:
            header, position = _take(data, position, 18)
            length = int.from_bytes(header[15:18], "little")
            block, position = _take(data, position, length)
            yield from _data_block(
                block,
                pilot_tstates=int.from_bytes(header[0:2], "little"),
                sync1_tstates=int.from_bytes(header[2:4], "little"),
                sync2_tstates=int.from_bytes(header[4:6], "little"),
                zero_tstates=int.from_bytes(header[6:8], "little"),
                one_tstates=int.from_bytes(header[8:10], "little"),
                pilot_pulses=int.from_bytes(header[10:12], "little"),
                used_bits_last_byte=header[12],
                pause_ms=int.from_bytes(header[13:15], "little"),
            )
        elif block_id == 0x12:
            block, position = _take(data, position, 4)
            pulse = int.from_bytes(block[0:2], "little")
            count = int.from_bytes(block[2:4], "little")
            yield PulseRun(pulse, count)
        elif block_id == 0x13:
            count, position = _number(data, position, 1)
            block, position = _take(data, position, count * 2)
            for offset in range(0, len(block), 2):
                yield Pulse(int.from_bytes(block[offset : offset + 2], "little"))
        elif block_id == 0x14:
            header, position = _take(data, position, 10)
            length = int.from_bytes(header[7:10], "little")
            block, position = _take(data, position, length)
            yield EncodedData(
                block,
                zero_tstates=int.from_bytes(header[0:2], "little"),
                one_tstates=int.from_bytes(header[2:4], "little"),
                used_bits_last_byte=header[4],
            )
            yield from _pause(int.from_bytes(header[5:7], "little"))
        elif block_id == 0x15:
            header, position = _take(data, position, 8)
            length = int.from_bytes(header[5:8], "little")
            block, position = _take(data, position, length)
            yield DirectRecording(
                int.from_bytes(header[0:2], "little"), block, header[4]
            )
            yield from _pause(int.from_bytes(header[2:4], "little"))
        elif block_id == 0x20:
            pause_ms, position = _number(data, position, 2)
            if pause_ms == 0:
                raise TapeDecodeError("TZX requests a manual tape stop")
            yield Pause(pause_ms)
        elif block_id == 0x30:
            length, position = _number(data, position, 1)
            _, position = _take(data, position, length)
        elif block_id == 0x32:
            length, position = _number(data, position, 2)
            _, position = _take(data, position, length)
        elif block_id == 0x21:
            length, position = _number(data, position, 1)
            _, position = _take(data, position, length)
        elif block_id == 0x22:
            continue
        elif block_id == 0x31:
            header, position = _take(data, position, 2)
            _, position = _take(data, position, header[1])
        elif block_id == 0x33:
            count, position = _number(data, position, 1)
            _, position = _take(data, position, count * 3)
        elif block_id == 0x35:
            _, position = _take(data, position, 16)
            length, position = _number(data, position, 4)
            _, position = _take(data, position, length)
        elif block_id == 0x5A:
            _, position = _take(data, position, 9)
        elif block_id in {0x18, 0x19, 0x2A, 0x2B}:
            length, position = _number(data, position, 4)
            _, position = _take(data, position, length)
            if block_id in {0x18, 0x19}:
                raise TapeDecodeError(f"TZX block 0x{block_id:02X} is not supported")
        elif block_id in {0x23, 0x24, 0x25, 0x26, 0x27, 0x28}:
            raise TapeDecodeError(
                f"TZX control-flow block 0x{block_id:02X} is not supported"
            )
        else:
            raise TapeDecodeError(f"unknown TZX block 0x{block_id:02X}")


def _data_block(
    data: bytes,
    *,
    pilot_tstates: int = 2168,
    sync1_tstates: int = 667,
    sync2_tstates: int = 735,
    zero_tstates: int = 855,
    one_tstates: int = 1710,
    pilot_pulses: int | None = None,
    used_bits_last_byte: int = 8,
    pause_ms: int = 1000,
) -> Iterator[TapeEvent]:
    if not data:
        raise TapeDecodeError("empty data block")
    if pilot_pulses is None:
        pilot_pulses = 8063 if data[0] < 0x80 else 3223
    yield PulseRun(pilot_tstates, pilot_pulses)
    yield Pulse(sync1_tstates)
    yield Pulse(sync2_tstates)
    yield EncodedData(data, zero_tstates, one_tstates, used_bits_last_byte)
    yield from _pause(pause_ms)


def _pause(milliseconds: int) -> Iterator[Pause]:
    if milliseconds:
        yield Pause(milliseconds)


def _number(data: bytes, position: int, size: int) -> tuple[int, int]:
    chunk, position = _take(data, position, size)
    return int.from_bytes(chunk, "little"), position


def _take(data: bytes, position: int, size: int) -> tuple[bytes, int]:
    end = position + size
    if size < 0 or end > len(data):
        raise TapeDecodeError(f"truncated tape image at byte {position}")
    return data[position:end], end
