"""Device-facing touch renderer with small operating-system status overlays."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import time

from zxdeck.system import primary_ipv4_address

from .renderer import RenderedScreen, TouchRenderer as BaseTouchRenderer


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
        self._cached_address = "NO NETWORK"
        self._address_checked_at = float("-inf")

    def _network_address(self) -> str:
        now = time.monotonic()
        if now - self._address_checked_at >= 5.0:
            self._cached_address = self._address_provider() or "NO NETWORK"
            self._address_checked_at = now
        return self._cached_address

    def render_settings(
        self,
        *,
        playback_device: str = "default",
        capture_device: str = "default",
        output_level: int = 25,
        offset: int = 0,
        ip_address: str | None = None,
    ) -> RenderedScreen:
        return super().render_settings(
            playback_device=playback_device,
            capture_device=capture_device,
            output_level=output_level,
            offset=offset,
            ip_address=ip_address or self._network_address(),
        )
