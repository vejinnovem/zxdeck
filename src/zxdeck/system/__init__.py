"""Small operating-system integration helpers used by ZX Deck frontends."""

from .network import ipv4_addresses, parse_ipv4_addresses, primary_ipv4_address

__all__ = ["ipv4_addresses", "parse_ipv4_addresses", "primary_ipv4_address"]
