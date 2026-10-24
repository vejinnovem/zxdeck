"""Fast filename-only index for tape images."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass
import json
import os
from pathlib import Path

from zxdeck.config import StorageConfig

from .saves import SAVES_DIRECTORY_NAME


class StorageUnavailable(RuntimeError):
    pass


INDEX_FILENAME = ".zxdeck-index.json"
INDEX_VERSION = 1


@dataclass(frozen=True, slots=True)
class TapeEntry:
    name: str
    path: Path

    @property
    def initial(self) -> str:
        first = self.name[:1].upper()
        return first if "A" <= first <= "Z" else "#"


class TapeLibrary:
    """Index names once, then search and group without touching the filesystem."""

    def __init__(
        self,
        config: StorageConfig,
        *,
        mount_check: Callable[[Path], bool] = os.path.ismount,
    ) -> None:
        self.config = config
        self._mount_check = mount_check
        self._entries: tuple[TapeEntry, ...] = ()

    @property
    def entries(self) -> tuple[TapeEntry, ...]:
        return self._entries

    def refresh(self) -> tuple[TapeEntry, ...]:
        root = self.config.path
        mount_path = self.config.mount_path or root
        if self.config.require_mount and not self._mount_check(mount_path):
            raise StorageUnavailable(f"storage path is not mounted: {mount_path}")
        if not root.is_dir():
            raise StorageUnavailable(f"storage directory does not exist: {root}")

        extensions = frozenset(self.config.extensions)
        indexed = load_tape_index(root, extensions) if self.config.recursive else None
        paths: Iterable[Path]
        if indexed is not None:
            paths = indexed
        elif self.config.recursive:
            paths = self._walk_main_library(root)
        else:
            paths = (
                Path(item.path)
                for item in os.scandir(root)
                if item.is_file(follow_symlinks=False)
            )

        entries = (
            TapeEntry(path.name, path)
            for path in paths
            if path.suffix.casefold() in extensions
        )
        self._entries = tuple(
            sorted(entries, key=lambda entry: (entry.name.casefold(), str(entry.path)))
        )
        return self._entries

    @staticmethod
    def _walk_main_library(root: Path) -> Iterable[Path]:
        """Walk the tape tree while pruning the dedicated top-level saves folder."""
        for directory, subdirectories, filenames in os.walk(root):
            directory_path = Path(directory)
            if directory_path == root:
                subdirectories[:] = [
                    name
                    for name in subdirectories
                    if name.casefold() != SAVES_DIRECTORY_NAME.casefold()
                ]
            for filename in filenames:
                yield directory_path / filename

    def search(self, query: str) -> tuple[TapeEntry, ...]:
        needle = query.casefold().strip()
        if not needle:
            return self._entries
        return tuple(entry for entry in self._entries if needle in entry.name.casefold())

    def by_initial(self) -> dict[str, tuple[TapeEntry, ...]]:
        grouped: dict[str, list[TapeEntry]] = defaultdict(list)
        for entry in self._entries:
            grouped[entry.initial].append(entry)
        return {initial: tuple(entries) for initial, entries in sorted(grouped.items())}


def load_tape_index(root: Path, extensions: frozenset[str]) -> tuple[Path, ...] | None:
    """Load a generated relative-path index, or fall back to scanning."""
    index_path = root / INDEX_FILENAME
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("version") != INDEX_VERSION:
        return None
    relative_paths = payload.get("paths")
    if not isinstance(relative_paths, list):
        return None

    paths: list[Path] = []
    for value in relative_paths:
        if not isinstance(value, str):
            return None
        relative = Path(value)
        if relative.is_absolute() or not relative.parts or ".." in relative.parts:
            return None
        if relative.parts[0].casefold() == SAVES_DIRECTORY_NAME.casefold():
            return None
        if relative.suffix.casefold() not in extensions:
            return None
        paths.append(root / relative)
    return tuple(paths)


def write_tape_index(root: Path, relative_paths: Iterable[Path]) -> Path:
    """Atomically write a portable index for a prepared tape directory."""
    paths = sorted(path.as_posix() for path in relative_paths)
    target = root / INDEX_FILENAME
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(
        json.dumps({"version": INDEX_VERSION, "paths": paths}, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(target)
    return target
