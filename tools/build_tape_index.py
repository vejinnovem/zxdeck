#!/usr/bin/env python3
"""Build a persistent filename index for an existing ZX Deck tape library."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


ROOT = Path(__file__).parents[1].resolve()
sys.path.insert(0, str(ROOT / "src"))

from zxdeck.config import DEFAULT_TAPE_EXTENSIONS
from zxdeck.storage import write_tape_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    return parser.parse_args()


def main() -> int:
    root = parse_args().directory.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"tape directory does not exist: {root}")
    extensions = frozenset(DEFAULT_TAPE_EXTENSIONS)
    relative_paths = (
        (Path(directory) / filename).relative_to(root)
        for directory, _subdirectories, filenames in os.walk(root)
        for filename in filenames
        if Path(filename).suffix.casefold() in extensions
    )
    target = write_tape_index(root, relative_paths)
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
