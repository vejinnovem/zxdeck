#!/usr/bin/env python3
"""Generate 240x320 PNG previews of the touch UI without Raspberry Pi hardware."""

from __future__ import annotations

import argparse
from pathlib import Path

from zxdeck.core.state import DeckState, TransportState
from zxdeck.frontends.touch import MultiTapEditor, TouchRenderer


MOCK_FILES = (
    "MANIC MINER.TZX",
    "JET SET WILLY.TAP",
    "ELITE.TZX",
    "DIZZY 3.TZX",
    "HEAD OVER HEELS.TZX",
    "SABOTEUR.TAP",
    "R-TYPE.TZX",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/ui-preview"),
        help="directory for generated PNG files",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=Path("assets/fonts/bescii.ttf"),
        help="optional pixel-font TTF; Pillow default is used if it is absent",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    font_path = args.font if args.font.exists() else None
    renderer = TouchRenderer(font_path=font_path)

    home = renderer.render_home(
        DeckState(
            transport=TransportState.PLAYING,
            tape_name="MANIC MINER.TZX",
            position_seconds=102,
            duration_seconds=196,
        )
    )
    home.image.save(args.output / "home.png")

    files = renderer.render_files(MOCK_FILES, selected=1)
    files.image.save(args.output / "files.png")

    editor = MultiTapEditor(text="MANIC_MINE")
    filename = renderer.render_filename(editor)
    filename.image.save(args.output / "filename.png")

    settings = renderer.render_settings()
    settings.image.save(args.output / "settings.png")

    print(f"Wrote UI previews to {args.output}")
    if font_path is None:
        print(
            "Note: no pixel font asset was found; previews use Pillow's fallback font. "
            "Add assets/fonts/bescii.ttf or pass --font PATH for the intended look."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
