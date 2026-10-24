"""Immutable public state published by the zxdeck backend."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum


class TransportState(str, Enum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    RECORDING = "recording"


@dataclass(frozen=True, slots=True)
class DeckState:
    revision: int = 0
    transport: TransportState = TransportState.STOPPED
    tape_name: str | None = None
    position_seconds: float = 0.0
    duration_seconds: float | None = None
    error: str | None = None
    segment_label: str | None = None
    segment_index: int = 0
    segment_count: int = 0

    def next_revision(self, **changes: object) -> "DeckState":
        return replace(self, revision=self.revision + 1, **changes)
