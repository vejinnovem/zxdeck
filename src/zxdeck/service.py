"""Generate systemd units for the checked-out ZX Deck application."""

from __future__ import annotations

from pathlib import Path


def render_systemd_unit(root: Path, user: str) -> str:
    root = root.resolve()
    python = root / ".venv" / "bin" / "python"
    tool = root / "tools" / "ui_touch_demo.py"
    hardware = root / "config" / "hardware.zxdeck-pi-zero.toml"
    application = root / "config" / "application.zxdeck-pi-zero.toml"
    return f"""[Unit]
Description=ZX Deck touchscreen application
Wants=zxdeck-splash.service
After=local-fs.target zxdeck-splash.service

[Service]
Type=simple
User={user}
Group={user}
SupplementaryGroups=spi gpio
WorkingDirectory={root}
Environment=PYTHONPATH={root / 'src'}
ExecStartPre=+/usr/bin/systemctl stop zxdeck-splash.service
ExecStart={python} {tool} --config {hardware} --app-config {application} --allow-poweroff
Restart=on-failure
RestartSec=2
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
"""


def render_systemd_splash_unit(root: Path, user: str) -> str:
    """Render an early-boot unit that holds the splash until the app starts."""
    root = root.resolve()
    python = root / ".venv" / "bin" / "python"
    tool = root / "tools" / "boot_splash.py"
    hardware = root / "config" / "hardware.zxdeck-pi-zero.toml"
    return f"""[Unit]
Description=ZX Deck early boot splash
DefaultDependencies=no
Requires=local-fs.target
After=local-fs.target systemd-udev-trigger.service
Before=basic.target

[Service]
Type=notify
NotifyAccess=main
User={user}
Group={user}
SupplementaryGroups=spi gpio
WorkingDirectory={root}
Environment=PYTHONPATH={root / 'src'}
ExecStart={python} {tool} --config {hardware} --hold
TimeoutStartSec=6
TimeoutStopSec=2

[Install]
WantedBy=basic.target
"""
