"""Application configuration independent of the Raspberry Pi hardware profile."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib


DEFAULT_TAPE_EXTENSIONS = (".tap", ".tzx", ".pzx")


@dataclass(frozen=True, slots=True)
class StorageConfig:
    path: Path = field(
        default_factory=lambda: Path("~/.local/share/zxdeck/tapes").expanduser()
    )
    require_mount: bool = False
    mount_path: Path | None = None
    browse_root: Path = Path("/")
    recursive: bool = True
    extensions: tuple[str, ...] = DEFAULT_TAPE_EXTENSIONS


@dataclass(frozen=True, slots=True)
class AudioConfig:
    capture_device: str = "default"
    playback_device: str = "default"


@dataclass(frozen=True, slots=True)
class AppConfig:
    storage: StorageConfig = field(default_factory=StorageConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    @classmethod
    def load(cls, path: str | Path) -> "AppConfig":
        config_path = Path(path).expanduser().resolve()
        with config_path.open("rb") as stream:
            data = tomllib.load(stream)

        storage_data = dict(data.get("storage", {}))
        storage_path = _resolve_path(
            storage_data.pop("path", "~/.local/share/zxdeck/tapes"),
            config_path.parent,
        )
        browse_root = _resolve_path(
            storage_data.pop("browse_root", "/"),
            config_path.parent,
        )
        mount_value = storage_data.pop("mount_path", None)
        mount_path = (
            _resolve_path(mount_value, config_path.parent)
            if mount_value is not None
            else None
        )
        extensions = tuple(
            _normalise_extension(item)
            for item in storage_data.pop("extensions", DEFAULT_TAPE_EXTENSIONS)
        )

        return cls(
            storage=StorageConfig(
                path=storage_path.resolve(),
                browse_root=browse_root,
                mount_path=mount_path,
                extensions=extensions,
                **storage_data,
            ),
            audio=AudioConfig(**data.get("audio", {})),
        )


def _normalise_extension(value: str) -> str:
    extension = value.casefold().strip()
    if not extension.startswith("."):
        extension = "." + extension
    return extension


def _resolve_path(value: str | Path, relative_to: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = relative_to / path
    return path.resolve()
