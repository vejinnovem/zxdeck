"""Small operating-system integration helpers used by ZX Deck frontends."""

from .network import ipv4_addresses, parse_ipv4_addresses, primary_ipv4_address
from .update import (
    SERVICE_NAME,
    SYSTEMCTL_PATH,
    UpdateResult,
    apply_update,
    check_for_update,
    render_update_sudoers,
    restart_zxdeck_service,
)

__all__ = [
    "SERVICE_NAME",
    "SYSTEMCTL_PATH",
    "UpdateResult",
    "apply_update",
    "check_for_update",
    "ipv4_addresses",
    "parse_ipv4_addresses",
    "primary_ipv4_address",
    "render_update_sudoers",
    "restart_zxdeck_service",
]
