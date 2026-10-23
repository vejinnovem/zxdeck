"""Small polling GPIO adapters without gpiozero's background threads."""

from __future__ import annotations

from typing import Any


class _LgpioDevice:
    def __init__(self, pin: int, *, chip: int = 0, module: Any = None) -> None:
        if module is None:
            import lgpio as module

        self._module = module
        self.pin = pin
        self._handle = module.gpiochip_open(chip)
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._module.gpio_free(self._handle, self.pin)
        self._module.gpiochip_close(self._handle)
        self._closed = True


class LgpioInputDevice(_LgpioDevice):
    """Active-low polled input compatible with the XPT2046 PENIRQ line."""

    def __init__(
        self,
        pin: int,
        pull_up: bool = False,
        *,
        chip: int = 0,
        module: Any = None,
    ) -> None:
        super().__init__(pin, chip=chip, module=module)
        flags = self._module.SET_PULL_UP if pull_up else self._module.SET_PULL_NONE
        self._module.gpio_claim_input(self._handle, pin, flags)

    @property
    def is_active(self) -> bool:
        return self._module.gpio_read(self._handle, self.pin) == 0


class LgpioOutputDevice(_LgpioDevice):
    """Minimal output implementing the on/off interface used by the LCD."""

    def __init__(
        self,
        pin: int,
        initial_value: bool = False,
        *,
        chip: int = 0,
        module: Any = None,
    ) -> None:
        super().__init__(pin, chip=chip, module=module)
        self._module.gpio_claim_output(self._handle, pin, int(initial_value))

    def on(self) -> None:
        self._module.gpio_write(self._handle, self.pin, 1)

    def off(self) -> None:
        self._module.gpio_write(self._handle, self.pin, 0)
