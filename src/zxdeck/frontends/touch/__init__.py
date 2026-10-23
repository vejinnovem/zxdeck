"""Local 240x320 touchscreen frontend for ZX Deck.

The base renderer remains hardware-independent. The public TouchRenderer adds
small read-only device status overlays (currently the IPv4 address) without
moving network management into the UI domain logic.
"""

from .controller import TouchUIController
from .device_renderer import DeviceTouchRenderer, TouchRenderer
from .keypad import InputMode, MultiTapEditor
from .renderer import Screen, TouchRenderer as BaseTouchRenderer

__all__ = [
    "BaseTouchRenderer",
    "DeviceTouchRenderer",
    "InputMode",
    "MultiTapEditor",
    "Screen",
    "TouchRenderer",
    "TouchUIController",
]
