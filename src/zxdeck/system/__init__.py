"""Small operating-system integration helpers used by ZX Deck frontends."""

from .network import (
    WifiNetwork,
    connect_wifi,
    connected_wifi_ssid,
    ipv4_addresses,
    parse_ipv4_addresses,
    parse_nmcli_wifi,
    primary_ipv4_address,
    scan_wifi_networks,
)
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
    "WifiNetwork",
    "apply_update",
    "check_for_update",
    "connect_wifi",
    "connected_wifi_ssid",
    "ipv4_addresses",
    "parse_ipv4_addresses",
    "parse_nmcli_wifi",
    "primary_ipv4_address",
    "render_update_sudoers",
    "restart_zxdeck_service",
    "scan_wifi_networks",
]
