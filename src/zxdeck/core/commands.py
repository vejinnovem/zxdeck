"""Frontend-to-backend command contract.

Concrete tape commands will be added with the tape/audio implementation. Both
future frontends must dispatch through this contract rather than owning that
logic themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class Command(Protocol):
    """Marker protocol for commands accepted by :class:`Backend`."""


@dataclass(frozen=True, slots=True)
class ClearError:
    """Clear a backend error after it has been shown by a frontend."""

