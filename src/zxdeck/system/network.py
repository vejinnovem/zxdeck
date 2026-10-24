"""Network diagnostics plus NetworkManager Wi-Fi helpers for the local UI."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
import subprocess


@dataclass(frozen=True, slots=True)
class WifiNetwork:
    ssid: str
    signal: int = 0
    security: str = ""
    active: bool = False

    @property
    def secured(self) -> bool:
        value = self.security.strip().casefold()
        return value not in {"", "--", "none", "open"}


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


def _split_nmcli_terse(line: str) -> list[str]:
    """Split nmcli -t output while honoring its backslash escaping."""
    fields: list[str] = []
    current: list[str] = []
    escaped = False
    for character in line.rstrip("\n"):
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == ":":
            fields.append("".join(current))
            current = []
        else:
            current.append(character)
    if escaped:
        current.append("\\")
    fields.append("".join(current))
    return fields


def parse_nmcli_wifi(output: str) -> tuple[WifiNetwork, ...]:
    """Parse `nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list`."""
    networks: dict[str, WifiNetwork] = {}
    for line in output.splitlines():
        fields = _split_nmcli_terse(line)
        if len(fields) < 4:
            continue
        in_use, ssid, signal_text, security = fields[:4]
        ssid = ssid.strip()
        if not ssid:
            continue
        try:
            signal = max(0, min(100, int(signal_text)))
        except ValueError:
            signal = 0
        candidate = WifiNetwork(
            ssid=ssid,
            signal=signal,
            security=security.strip(),
            active=in_use.strip().casefold() in {"*", "yes"},
        )
        previous = networks.get(ssid)
        if previous is None or candidate.active or candidate.signal > previous.signal:
            networks[ssid] = candidate
    return tuple(
        sorted(
            networks.values(),
            key=lambda item: (not item.active, -item.signal, item.ssid.casefold()),
        )
    )


def _nmcli(
    *args: str,
    timeout: float = 15.0,
) -> subprocess.CompletedProcess[str] | None:
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    try:
        return subprocess.run(
            ("nmcli", *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def scan_wifi_networks(
    *,
    rescan: bool = True,
    timeout: float = 15.0,
) -> tuple[WifiNetwork, ...]:
    """Return visible Wi-Fi networks using NetworkManager, strongest first."""
    result = _nmcli(
        "-t",
        "-f",
        "IN-USE,SSID,SIGNAL,SECURITY",
        "device",
        "wifi",
        "list",
        "--rescan",
        "yes" if rescan else "no",
        timeout=timeout,
    )
    if result is None or result.returncode != 0:
        return ()
    return parse_nmcli_wifi(result.stdout)


def connected_wifi_ssid(*, timeout: float = 3.0) -> str | None:
    for network in scan_wifi_networks(rescan=False, timeout=timeout):
        if network.active:
            return network.ssid
    return None


def connect_wifi(
    ssid: str,
    password: str = "",
    *,
    timeout: float = 30.0,
) -> tuple[bool, str]:
    """Connect through NetworkManager without storing credentials in ZX Deck."""
    ssid = ssid.strip()
    if not ssid:
        return False, "NO SSID SELECTED"
    command = ["--wait", str(max(1, int(timeout))), "device", "wifi", "connect", ssid]
    if password:
        command.extend(("password", password))
    result = _nmcli(*command, timeout=timeout + 5.0)
    if result is None:
        return False, "NMCLI UNAVAILABLE"
    detail = (result.stderr or result.stdout).strip()
    if result.returncode != 0:
        return False, detail or f"nmcli exited with {result.returncode}"
    return True, detail or "CONNECTED"
