"""Read-only network diagnostics for the local ZX Deck frontend."""

from __future__ import annotations

import ipaddress
import subprocess


def parse_ipv4_addresses(output: str) -> tuple[str, ...]:
    """Return unique, non-loopback IPv4 addresses from `hostname -I` output."""
    addresses: list[str] = []
    for token in output.split():
        candidate = token.split("%", 1)[0]
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if not isinstance(address, ipaddress.IPv4Address) or address.is_loopback:
            continue
        value = str(address)
        if value not in addresses:
            addresses.append(value)
    return tuple(addresses)


def ipv4_addresses(*, timeout: float = 1.0) -> tuple[str, ...]:
    """Ask the OS for local addresses without depending on NetworkManager."""
    try:
        result = subprocess.run(
            ("hostname", "-I"),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if result.returncode != 0:
        return ()
    return parse_ipv4_addresses(result.stdout)


def primary_ipv4_address(*, timeout: float = 1.0) -> str | None:
    """Return the first usable IPv4 address reported by the operating system."""
    addresses = ipv4_addresses(timeout=timeout)
    return addresses[0] if addresses else None
