#!/usr/bin/env python3
"""Install and enable zxdeck.service for the current checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import pwd
import subprocess
import sys


ROOT = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(ROOT / "src"))

from zxdeck.service import render_systemd_unit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--user",
        default=os.environ.get("SUDO_USER") or os.environ.get("USER"),
        help="unprivileged account that owns the checkout and hardware access",
    )
    parser.add_argument(
        "--unit-path",
        type=Path,
        default=Path("/etc/systemd/system/zxdeck.service"),
    )
    parser.add_argument("--no-start", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run this installer through sudo")
    if not args.user:
        raise SystemExit("could not determine service user; pass --user")
    pwd.getpwnam(args.user)

    required = (
        ROOT / ".venv" / "bin" / "python",
        ROOT / "tools" / "ui_touch_demo.py",
        ROOT / "config" / "hardware.zxdeck-pi-zero.toml",
        ROOT / "config" / "application.zxdeck-pi-zero.toml",
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing required files: " + ", ".join(missing))

    unit = render_systemd_unit(ROOT, args.user)
    temporary = args.unit_path.with_suffix(".service.tmp")
    temporary.write_text(unit, encoding="utf-8")
    os.chmod(temporary, 0o644)
    temporary.replace(args.unit_path)
    subprocess.run(("systemctl", "daemon-reload"), check=True)
    if not args.no_start:
        subprocess.run(("systemctl", "enable", "--now", "zxdeck.service"), check=True)
    print(f"Installed {args.unit_path} for user {args.user}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
