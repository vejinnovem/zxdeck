"""Dedicated save-file library kept separate from the main tape collection."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


SAVES_DIRECTORY_NAME = "saves"
SAVE_EXTENSIONS = frozenset((".wav", ".tap", ".tzx", ".pzx"))


@dataclass(frozen=True, slots=True)
class SaveEntry:
    name: str
    path: Path


def saves_directory(root: str | Path) -> Path:
    return Path(root) / SAVES_DIRECTORY_NAME


def list_save_entries(root: str | Path) -> tuple[SaveEntry, ...]:
    """Return supported files from the dedicated saves subtree, sorted by name."""
    directory = saves_directory(root)
    if not directory.is_dir():
        return ()

    entries = (
        SaveEntry(Path(base, filename).name, Path(base, filename))
        for base, _subdirectories, filenames in os.walk(directory)
        for filename in filenames
        if Path(filename).suffix.casefold() in SAVE_EXTENSIONS
    )
    return tuple(
        sorted(entries, key=lambda entry: (entry.name.casefold(), str(entry.path)))
    )
