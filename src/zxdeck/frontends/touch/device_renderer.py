"""Device-facing touch renderer with small operating-system status overlays."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from zxdeck.system import primary_ipv4_address

from .renderer import CYAN, RenderedScreen, TouchRenderer as BaseTouchRenderer


class DeviceTouchRenderer(BaseTouchRenderer):
    """Add read-only device status to the hardware-independent base renderer."""

    def __init__(
        self,
        *,
        font_path: str | Path | None = None,
        address_provider: Callable[[], str | None] = primary_ipv4_address,
    ) -> None:
        super().__init__(font_path=font_path)
        self._address_provider = address_provider

    def render_settings(
        self,
        *,
        playback_device: str = "default",
        capture_device: str = "default",
    ) -> RenderedScreen:
        rendered = super().render_settings(
            playback_device=playback_device,
            capture_device=capture_device,
        )
        from PIL import ImageDraw

        address = self._address_provider() or "NO NETWORK"
        draw = ImageDraw.Draw(rendered.image)
        self._center_text(draw, f"IP {address}", 198, size=7, fill=CYAN)
        return rendered


# Keep the public frontend API simple: device applications import TouchRenderer
# from zxdeck.frontends.touch, while tests or future adapters can still import
# the hardware-independent base renderer directly from .renderer.
TouchRenderer = DeviceTouchRenderer
