#!/usr/bin/env python3
"""Install and enable ZX Deck systemd services for the current checkout."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import pwd
import subprocess
import sys


ROOT = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(ROOT / "src"))

from zxdeck.service import render_systemd_splash_unit, render_systemd_unit


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
    parser.add_argument(
        "--splash-unit-path",
        type=Path,
        default=Path("/etc/systemd/system/zxdeck-splash.service"),
    )
    parser.add_argument(
        "--no-boot-splash",
        action="store_true",
        help="do not install the early boot splash service",
    )
    parser.add_argument("--no-start", action="store_true")
    return parser.parse_args()


def write_unit(path: Path, content: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o644)
    temporary.replace(path)


def main() -> int:
    args = parse_args()
    if os.geteuid() != 0:
        raise SystemExit("run this installer through sudo")
    if not args.user:
        raise SystemExit("could not determine service user; pass --user")
    pwd.getpwnam(args.user)

    required = [
        ROOT / ".venv" / "bin" / "python",
        ROOT / "tools" / "ui_touch_demo.py",
        ROOT / "config" / "hardware.zxdeck-pi-zero.toml",
        ROOT / "config" / "application.zxdeck-pi-zero.toml",
    ]
    if not args.no_boot_splash:
        required.extend(
            (
                ROOT / "tools" / "boot_splash.py",
                ROOT / "assets" / "branding" / "zxdeck.png",
            )
        )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing required files: " + ", ".join(missing))

    write_unit(args.unit_path, render_systemd_unit(ROOT, args.user))

    if args.no_boot_splash:
        subprocess.run(
            ("systemctl", "disable", "zxdeck-splash.service"),
            check=False,
        )
        if args.splash_unit_path.exists():
            args.splash_unit_path.unlink()
    else:
        write_unit(
            args.splash_unit_path,
            render_systemd_splash_unit(ROOT, args.user),
        )

    subprocess.run(("systemctl", "daemon-reload"), check=True)
    if not args.no_start:
        if not args.no_boot_splash:
            subprocess.run(("systemctl", "enable", "zxdeck-splash.service"), check=True)
        subprocess.run(("systemctl", "enable", "--now", "zxdeck.service"), check=True)

    print(f"Installed {args.unit_path} for user {args.user}")
    if args.no_boot_splash:
        print("Early boot splash disabled.")
    else:
        print(f"Installed {args.splash_unit_path}; it will run on the next boot.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
