#!/usr/bin/env python3
"""Apply or restore the verified Raspberry Pi OS Lite boot optimizations."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1].resolve()
CLOUD_INIT_MARKER = Path("/etc/cloud/cloud-init.disabled")
SWAP_CONFIG = Path("/etc/rpi/swap.conf.d/90-zxdeck.conf")
SWAP_SOURCE = ROOT / "config" / "system" / "90-zxdeck-swap.conf"
OPTIONAL_UNITS = ("bluetooth.service", "NetworkManager-wait-online.service")


def write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.chmod(temporary, 0o644)
    temporary.replace(path)


def apply_optimizations(
    cloud_marker: Path = CLOUD_INIT_MARKER,
    swap_config: Path = SWAP_CONFIG,
    swap_source: Path = SWAP_SOURCE,
) -> None:
    if not Path("/etc/rpi/swap.conf").is_file() and swap_config == SWAP_CONFIG:
        raise SystemExit("rpi-swap is unavailable; this optimization supports Raspberry Pi OS only")
    write_atomic(cloud_marker, b"")
    write_atomic(swap_config, swap_source.read_bytes())
    subprocess.run(("systemctl", "disable", *OPTIONAL_UNITS), check=True)


def restore_defaults(
    cloud_marker: Path = CLOUD_INIT_MARKER,
    swap_config: Path = SWAP_CONFIG,
) -> None:
    cloud_marker.unlink(missing_ok=True)
    swap_config.unlink(missing_ok=True)
    subprocess.run(("systemctl", "enable", *OPTIONAL_UNITS), check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--restore",
        action="store_true",
        help="restore Raspberry Pi OS defaults instead of applying optimizations",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run this tool through sudo")
    if args.restore:
        restore_defaults()
        print("Restored Raspberry Pi OS boot defaults. Reboot to apply them.")
    else:
        apply_optimizations()
        print("Installed ZX Deck boot optimizations. Reboot to apply them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
