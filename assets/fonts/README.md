# Fonts

ZX Deck's touch UI is designed for an 8x8-style retro bitmap/pixel face, but the
renderer does not hard-code any particular font.

Do not copy the original ZX Spectrum ROM font into this repository unless its
redistribution basis has been checked explicitly. For development,
`tools/ui_preview.py` and `tools/ui_touch_demo.py` look for
`assets/fonts/bescii.ttf`; if it is absent they fall back to Pillow's built-in
font.

BESCII by Damian Vila is a convenient CC0-licensed development font. It is not
intended to settle the final visual choice: a closer Spectrum-style font with a
clear redistribution licence can replace it without changing the renderer.
