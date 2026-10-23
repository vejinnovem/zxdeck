"""Constrained directory navigation for the touchscreen path picker."""

from __future__ import annotations

from pathlib import Path


class DirectoryUnavailable(RuntimeError):
    pass


class DirectoryBrowser:
    def __init__(self, root: Path, current: Path | None = None) -> None:
        self.root = root.expanduser().resolve()
        self.current = (current or self.root).expanduser().resolve()
        self._require_inside_root(self.current)

    def directories(self) -> tuple[str, ...]:
        try:
            items = (
                item.name
                for item in self.current.iterdir()
                if item.is_dir() and not item.name.startswith(".")
            )
            return tuple(sorted(items, key=str.casefold))
        except OSError as exc:
            raise DirectoryUnavailable(str(exc)) from exc

    def enter(self, name: str) -> Path:
        if name in {"", ".", ".."} or "/" in name:
            raise DirectoryUnavailable("invalid directory name")
        target = (self.current / name).resolve()
        self._require_inside_root(target)
        if not target.is_dir():
            raise DirectoryUnavailable(f"directory does not exist: {target}")
        self.current = target
        return target

    def parent(self) -> Path:
        if self.current != self.root:
            target = self.current.parent.resolve()
            self._require_inside_root(target)
            self.current = target
        return self.current

    def _require_inside_root(self, path: Path) -> None:
        if path != self.root and self.root not in path.parents:
            raise DirectoryUnavailable(f"directory is outside browse root: {path}")
