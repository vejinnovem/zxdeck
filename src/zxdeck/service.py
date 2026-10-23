"""Generate a systemd unit for the checked-out zxdeck application."""

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
After=local-fs.target

[Service]
Type=simple
User={user}
Group={user}
SupplementaryGroups=spi gpio
WorkingDirectory={root}
Environment=PYTHONPATH={root / 'src'}
ExecStart={python} {tool} --config {hardware} --app-config {application} --allow-poweroff
Restart=on-failure
RestartSec=2
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
"""
