"""Procedural ZX Deck splash renderer.

The repository keeps an SVG preview for humans. The runtime renders the same
240x320 design with Pillow so no binary image asset has to be committed.
"""

from __future__ import annotations


def render_splash(width: int = 240, height: int = 320):
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new("RGB", (width, height), "black")
    draw = ImageDraw.Draw(image)

    # Spectrum-inspired four-colour diagonal ribbon.
    bands = (
        ("#ff1b17", 0, 28, 166, 194),
        ("#ffd91a", 28, 56, 194, 222),
        ("#25c842", 56, 84, 222, 250),
        ("#24a9e8", 84, 112, 250, 278),
    )
    for color, bottom_left, bottom_right, top_left, top_right in bands:
        draw.polygon(
            [
                (bottom_left, height),
                (bottom_right, height),
                (top_right, 0),
                (top_left, 0),
            ],
            fill=color,
        )

    # Horizontal wordmark panel. The exact Spectrum-like UI font is supplied
    # separately; this fallback deliberately stays simple and straight.
    draw.rectangle((12, 126, width - 12, 194), fill="black")
    try:
        font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 34)
    except OSError:
        font = ImageFont.load_default()
    text = "ZX Deck"
    box = draw.textbbox((0, 0), text, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    draw.text(
        ((width - text_width) // 2, 160 - text_height // 2 - box[1]),
        text,
        font=font,
        fill="white",
    )
    return image
