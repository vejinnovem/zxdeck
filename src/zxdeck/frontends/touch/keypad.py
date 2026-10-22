"""Classic mobile-phone multi-tap text entry used by the touch UI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import monotonic


class InputMode(str, Enum):
    LOWER = "abc"
    UPPER = "ABC"
    NUMERIC = "123"


_BASE_MAP: dict[str, str] = {
    "1": ".,?!1",
    "2": "ABC2",
    "3": "DEF3",
    "4": "GHI4",
    "5": "JKL5",
    "6": "MNO6",
    "7": "PQRS7",
    "8": "TUV8",
    "9": "WXYZ9",
    "0": " 0_-",
}


@dataclass(slots=True)
class MultiTapEditor:
    """Edit a string using Nokia-era repeated key presses.

    The currently selected character is inserted immediately and replaced when
    the same key is pressed again inside ``timeout_seconds``. This makes the
    editor easy to render because ``text`` always contains exactly what the user
    currently sees.
    """

    text: str = ""
    mode: InputMode = InputMode.UPPER
    timeout_seconds: float = 0.8
    max_length: int = 32
    _pending_key: str | None = None
    _pending_index: int = 0
    _last_press_at: float | None = None

    def press(self, key: str, *, now: float | None = None) -> str:
        if now is None:
            now = monotonic()

        if key == "*":
            self._clear_pending()
            self.text = self.text[:-1]
            return self.text

        if key == "#":
            self._clear_pending()
            self.mode = {
                InputMode.LOWER: InputMode.UPPER,
                InputMode.UPPER: InputMode.NUMERIC,
                InputMode.NUMERIC: InputMode.LOWER,
            }[self.mode]
            return self.text

        if key not in _BASE_MAP:
            raise ValueError(f"unsupported keypad key: {key!r}")

        chars = self._chars_for_key(key)
        can_cycle = (
            self._pending_key == key
            and self._last_press_at is not None
            and now - self._last_press_at <= self.timeout_seconds
            and bool(self.text)
        )

        if can_cycle:
            self._pending_index = (self._pending_index + 1) % len(chars)
            self.text = self.text[:-1] + chars[self._pending_index]
        else:
            self._clear_pending()
            if len(self.text) >= self.max_length:
                return self.text
            self._pending_key = key
            self._pending_index = 0
            self.text += chars[0]

        self._last_press_at = now
        return self.text

    def commit_pending(self) -> None:
        self._clear_pending()

    def expire(self, *, now: float | None = None) -> bool:
        """Commit a pending character when its multi-tap timeout has elapsed."""
        if self._pending_key is None or self._last_press_at is None:
            return False
        if now is None:
            now = monotonic()
        if now - self._last_press_at <= self.timeout_seconds:
            return False
        self._clear_pending()
        return True

    @property
    def has_pending_character(self) -> bool:
        return self._pending_key is not None

    def _chars_for_key(self, key: str) -> str:
        if self.mode is InputMode.NUMERIC:
            return key
        chars = _BASE_MAP[key]
        if self.mode is InputMode.LOWER:
            chars = "".join(char.lower() if char.isalpha() else char for char in chars)
        return chars

    def _clear_pending(self) -> None:
        self._pending_key = None
        self._pending_index = 0
        self._last_press_at = None
