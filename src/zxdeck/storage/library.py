"""Fast filename-only index for tape images."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
import json
import os
from pathlib import Path

from zxdeck.config import StorageConfig

from .saves import SAVES_DIRECTORY_NAME


class StorageUnavailable(RuntimeError):
    pass


INDEX_FILENAME = ".zxdeck-index.json"
INDEX_VERSION = 2
ProgressCallback = Callable[[str, int], None]


class IndexedPaths(Sequence[Path]):
    """Create Path objects only for entries the controller actually selects."""

    def __init__(self, root: Path, relative_paths: Sequence[str]) -> None:
        self._root = root
        self._relative_paths = relative_paths

    def __len__(self) -> int:
        return len(self._relative_paths)

    @property
    def relative_paths(self) -> Sequence[str]:
        return self._relative_paths

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(self._root / value for value in self._relative_paths[index])
        return self._root / self._relative_paths[index]


@dataclass(frozen=True, slots=True)
class TapeCatalog:
    names: Sequence[str]
    paths: Sequence[Path]


@dataclass(frozen=True, slots=True)
class TapeEntry:
    name: str
    _path: Path | None
    _root: Path | None = None
    _relative_path: str | None = None

    @classmethod
    def indexed(cls, name: str, root: Path, relative_path: str) -> "TapeEntry":
        return cls(name, None, root, relative_path)

    @property
    def path(self) -> Path:
        if self._path is not None:
            return self._path
        if self._root is None or self._relative_path is None:
            raise RuntimeError("indexed tape entry has no path")
        return self._root / self._relative_path

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

    def catalog(self, progress: ProgressCallback | None = None) -> TapeCatalog:
        """Return a UI-ready catalog, using lazy paths for a generated index."""
        root = self.config.path
        mount_path = self.config.mount_path or root
        if self.config.require_mount and not self._mount_check(mount_path):
            raise StorageUnavailable(f"storage path is not mounted: {mount_path}")
        if not root.is_dir():
            raise StorageUnavailable(f"storage directory does not exist: {root}")

        if progress is not None:
            progress("LOADING INDEX", 0)
        if self.config.recursive:
            indexed = load_tape_catalog(root, frozenset(self.config.extensions))
            if indexed is not None:
                if progress is not None:
                    progress("INDEX READY", len(indexed.names))
                return indexed

        entries = self.refresh(progress=progress)
        return TapeCatalog(
            tuple(entry.name for entry in entries),
            tuple(entry.path for entry in entries),
        )

    def refresh(
        self,
        progress: ProgressCallback | None = None,
    ) -> tuple[TapeEntry, ...]:
        root = self.config.path
        mount_path = self.config.mount_path or root
        if self.config.require_mount and not self._mount_check(mount_path):
            raise StorageUnavailable(f"storage path is not mounted: {mount_path}")
        if not root.is_dir():
            raise StorageUnavailable(f"storage directory does not exist: {root}")

        extensions = frozenset(self.config.extensions)
        if progress is not None:
            progress("LOADING INDEX", 0)
        indexed = load_tape_index(root, extensions) if self.config.recursive else None
        if indexed is not None:
            self._entries = indexed
            if progress is not None:
                progress("INDEX READY", len(indexed))
            return self._entries

        paths: Iterable[Path]
        if self.config.recursive:
            paths = self._walk_main_library(root, progress)
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
        if self.config.recursive:
            try:
                write_tape_index(
                    root,
                    (entry.path.relative_to(root) for entry in self._entries),
                )
            except OSError:
                pass
        if progress is not None:
            progress("INDEX READY", len(self._entries))
        return self._entries

    @staticmethod
    def _walk_main_library(
        root: Path,
        progress: ProgressCallback | None = None,
    ) -> Iterable[Path]:
        """Walk the tape tree while pruning the dedicated top-level saves folder."""
        count = 0
        for directory, subdirectories, filenames in os.walk(root):
            directory_path = Path(directory)
            if directory_path == root:
                subdirectories[:] = [
                    name
                    for name in subdirectories
                    if name.casefold() != SAVES_DIRECTORY_NAME.casefold()
                ]
            for filename in filenames:
                count += 1
                if progress is not None and count % 256 == 0:
                    progress("INDEXING TAPES", count)
                yield directory_path / filename
        if progress is not None:
            progress("INDEXING TAPES", count)

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


def load_tape_index(
    root: Path,
    extensions: frozenset[str],
) -> tuple[TapeEntry, ...] | None:
    """Load a generated relative-path index, or fall back to scanning."""
    catalog = load_tape_catalog(root, extensions)
    if catalog is None:
        return None
    if not isinstance(catalog.paths, IndexedPaths):
        return None
    return tuple(
        TapeEntry.indexed(name, root, relative)
        for name, relative in zip(
            catalog.names,
            catalog.paths.relative_paths,
            strict=True,
        )
    )


def load_tape_catalog(
    root: Path,
    extensions: frozenset[str],
) -> TapeCatalog | None:
    """Load pre-sorted names plus paths that remain strings until selected."""
    index_path = root / INDEX_FILENAME
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("version") != INDEX_VERSION:
        return None
    indexed_entries = payload.get("entries")
    if not isinstance(indexed_entries, list):
        return None

    names: list[str] = []
    relative_paths: list[str] = []
    for value in indexed_entries:
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not all(isinstance(item, str) for item in value)
        ):
            return None
        name, relative_value = value
        parts = relative_value.split("/")
        if (
            not relative_value
            or relative_value.startswith("/")
            or any(part in {"", ".", ".."} for part in parts)
        ):
            return None
        if parts[0].casefold() == SAVES_DIRECTORY_NAME.casefold():
            return None
        if not any(name.casefold().endswith(extension) for extension in extensions):
            return None
        if name != parts[-1]:
            return None
        names.append(name)
        relative_paths.append(relative_value)
    return TapeCatalog(tuple(names), IndexedPaths(root, relative_paths))


def write_tape_index(root: Path, relative_paths: Iterable[Path]) -> Path:
    """Atomically write a portable index for a prepared tape directory."""
    paths = sorted(
        relative_paths,
        key=lambda path: (path.name.casefold(), path.as_posix()),
    )
    entries = [[path.name, path.as_posix()] for path in paths]
    target = root / INDEX_FILENAME
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(
        json.dumps(
            {"version": INDEX_VERSION, "entries": entries},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    temporary.replace(target)
    return target
