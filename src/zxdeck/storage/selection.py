"""Persist the directory selected in the device UI outside the checkout."""

from __future__ import annotations

from pathlib import Path


def load_selected_path(state_file: Path, default: Path, browse_root: Path) -> Path:
    try:
        value = state_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return default.resolve()
    if not value:
        return default.resolve()
    selected = Path(value).expanduser().resolve()
    root = browse_root.expanduser().resolve()
    if selected != root and root not in selected.parents:
        return default.resolve()
    return selected


def save_selected_path(state_file: Path, selected: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = state_file.with_suffix(state_file.suffix + ".tmp")
    temporary.write_text(str(selected.resolve()) + "\n", encoding="utf-8")
    temporary.replace(state_file)
