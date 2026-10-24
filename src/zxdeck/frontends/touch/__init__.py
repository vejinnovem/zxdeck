"""Local 240x320 touchscreen frontend for ZX Deck.

The base renderer/controller stay hardware-independent. Device variants add
operating-system status and controls used on the Raspberry Pi appliance.
"""

from .controller import TouchUIController as BaseTouchUIController
from .device_controller import DeviceTouchUIController
from .device_renderer import DeviceTouchRenderer
from .keypad import InputMode, MultiTapEditor
from .renderer import Screen, TouchRenderer

TouchUIController = DeviceTouchUIController

__all__ = [
    "BaseTouchUIController",
    "DeviceTouchRenderer",
    "DeviceTouchUIController",
    "InputMode",
    "MultiTapEditor",
    "Screen",
    "TouchRenderer",
    "TouchUIController",
]
