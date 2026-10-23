"""Local 240x320 touchscreen frontend for ZX Deck.

The touch frontend is deliberately split from the backend and from Raspberry Pi
hardware access. Renderers produce ordinary RGB images first; a display adapter
can later convert those frames to RGB565 for the ILI9341-compatible driver.
"""

from .controller import TouchUIController
from .keypad import InputMode, MultiTapEditor
from .renderer import Screen, TouchRenderer

__all__ = [
    "InputMode",
    "MultiTapEditor",
    "Screen",
    "TouchRenderer",
    "TouchUIController",
]
