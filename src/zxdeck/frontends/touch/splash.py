"""ZX Deck splash loader for the touch UI."""

from __future__ import annotations

from pathlib import Path


DEFAULT_SPLASH = (
    Path(__file__).resolve().parents[4]
    / "assets"
    / "branding"
    / "zxdeck.png"
)


def render_splash(width: int = 240, height: int = 320):
    """Load the production splash asset and fit it to the TFT without smoothing."""
    from PIL import Image, ImageOps

    if not DEFAULT_SPLASH.is_file():
        raise FileNotFoundError(f"ZX Deck splash asset not found: {DEFAULT_SPLASH}")

    with Image.open(DEFAULT_SPLASH) as source:
        image = source.convert("RGB")

    if image.size != (width, height):
        image = ImageOps.fit(
            image,
            (width, height),
            method=Image.Resampling.NEAREST,
            centering=(0.5, 0.5),
        )

    return image
