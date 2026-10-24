"""Runtime touchscreen renderer state that should survive full Home redraws."""

from __future__ import annotations

from .device_renderer import DeviceTouchRenderer as BaseDeviceTouchRenderer
from .renderer import TAPE_TITLE_RECT


class DeviceTouchRenderer(BaseDeviceTouchRenderer):
    """Preserve the current title-marquee position across progress redraws.

    Playback progress causes full Home frames to be rendered. The base Home
    renderer draws the tape title at offset zero, which previously made a
    scrolling long filename visibly jump back to its beginning on every
    progress event. The runtime wrapper remembers the offset last requested by
    the marquee loop and reapplies it after a full Home render.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._runtime_title_name: str | None = None
        self._runtime_title_offset = 0

    def render_tape_title(self, tape_name: str, *, offset: int = 0):
        if tape_name != self._runtime_title_name:
            self._runtime_title_name = tape_name
            self._runtime_title_offset = 0
        self._runtime_title_offset = max(0, int(offset))
        return super().render_tape_title(tape_name, offset=offset)

    def render_home(self, state):
        tape_name = state.tape_name or "NO TAPE"
        saved_offset = (
            self._runtime_title_offset
            if tape_name == self._runtime_title_name
            else 0
        )

        rendered = super().render_home(state)

        if saved_offset:
            title = super().render_tape_title(
                tape_name,
                offset=saved_offset,
            )
            rendered.image.paste(title, TAPE_TITLE_RECT[:2])

        self._runtime_title_name = tape_name
        self._runtime_title_offset = saved_offset
        return rendered
