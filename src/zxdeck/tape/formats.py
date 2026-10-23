"""Lightweight structural checks used before tape images reach the device."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TapeProbe:
    declared_format: str
    detected_format: str | None
    valid: bool
    blocks: int = 0
    checksum_failures: int = 0
    reason: str = ""

    @property
    def canonical_suffix(self) -> str | None:
        return f".{self.detected_format}" if self.detected_format else None

    @property
    def strict(self) -> bool:
        return self.valid and self.checksum_failures == 0


def probe_tape_bytes(data: bytes, suffix: str) -> TapeProbe:
    declared = suffix.casefold().lstrip(".")
    if data.startswith(b"ZXTape!\x1a"):
        return TapeProbe(
            declared,
            "tzx",
            len(data) >= 10,
            reason="TZX header" if len(data) >= 10 else "truncated TZX header",
        )
    if data.startswith(b"PZXT"):
        return TapeProbe(
            declared,
            "pzx",
            len(data) >= 8,
            reason="PZX header" if len(data) >= 8 else "truncated PZX header",
        )

    tap = _probe_tap(data)
    if tap.valid:
        return TapeProbe(
            declared,
            "tap",
            True,
            blocks=tap.blocks,
            checksum_failures=tap.checksum_failures,
            reason="TAP block stream",
        )
    return TapeProbe(
        declared,
        None,
        False,
        blocks=tap.blocks,
        reason=tap.reason,
    )


def _probe_tap(data: bytes) -> TapeProbe:
    position = 0
    blocks = 0
    checksum_failures = 0
    while position + 2 <= len(data):
        length = int.from_bytes(data[position : position + 2], "little")
        position += 2
        if length == 0:
            return TapeProbe("tap", None, False, blocks, reason="zero-length block")
        if position + length > len(data):
            return TapeProbe(
                "tap",
                None,
                False,
                blocks,
                reason=f"block exceeds file at byte {position - 2}",
            )
        block = data[position : position + length]
        checksum = 0
        for value in block:
            checksum ^= value
        checksum_failures += checksum != 0
        position += length
        blocks += 1

    if not blocks:
        return TapeProbe("tap", None, False, reason="no TAP blocks")
    if position != len(data):
        return TapeProbe(
            "tap",
            None,
            False,
            blocks,
            reason=f"trailing byte at {position}",
        )
    return TapeProbe(
        "tap",
        "tap",
        True,
        blocks,
        checksum_failures,
        "TAP block stream",
    )
