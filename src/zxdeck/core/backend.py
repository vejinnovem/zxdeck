"""Single authoritative state model for touch and web frontends."""

from __future__ import annotations

from collections.abc import Callable
from threading import RLock
from typing import TypeVar

from .commands import ClearError, Command
from .state import DeckState


StateListener = Callable[[DeckState], None]
CommandType = TypeVar("CommandType", bound=Command)
CommandHandler = Callable[[Command], DeckState]


class UnsupportedCommand(ValueError):
    pass


class Backend:
    """Own state and serialize commands from every frontend.

    Hardware, tape, audio and storage services can register command handlers.
    Frontends only dispatch commands and subscribe to immutable snapshots.
    """

    def __init__(self, initial_state: DeckState | None = None) -> None:
        self._state = initial_state or DeckState()
        self._handlers: dict[type[object], CommandHandler] = {}
        self._listeners: list[StateListener] = []
        self._lock = RLock()
        self.register_handler(ClearError, self._clear_error)

    @property
    def state(self) -> DeckState:
        with self._lock:
            return self._state

    def subscribe(self, listener: StateListener) -> Callable[[], None]:
        with self._lock:
            self._listeners.append(listener)
            snapshot = self._state
        listener(snapshot)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners:
                    self._listeners.remove(listener)

        return unsubscribe

    def register_handler(
        self,
        command_type: type[CommandType],
        handler: Callable[[CommandType], DeckState],
    ) -> None:
        with self._lock:
            self._handlers[command_type] = handler  # type: ignore[assignment]

    def dispatch(self, command: Command) -> DeckState:
        with self._lock:
            handler = self._handlers.get(type(command))
            if handler is None:
                raise UnsupportedCommand(type(command).__name__)
            next_state = handler(command)
            if next_state.revision <= self._state.revision:
                next_state = next_state.next_revision()
            self._state = next_state
            listeners = tuple(self._listeners)
        for listener in listeners:
            listener(next_state)
        return next_state

    def _clear_error(self, _command: Command) -> DeckState:
        return self._state.next_revision(error=None)

