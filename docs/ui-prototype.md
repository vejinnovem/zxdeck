# ZX Deck UI prototype

The first UI milestone is intentionally independent of tape parsing, audio and
storage. It uses mock data so the 240x320 touchscreen ergonomics can be tested
before those services exist.

## Design rules

- Portrait canvas: 240x320 pixels.
- Large touch targets; do not design a miniature desktop interface.
- Retro 8x8-style typography is part of the visual language.
- The local touchscreen and web frontend should present the same device UI by
  default. The web frontend may later add administration-only affordances.
- Text entry on the TFT always uses the ZX Deck 3x4 multi-tap keypad.
- The web frontend may choose between the same 3x4 keypad and the browser/
  operating-system keyboard. This choice belongs to the web frontend, not the
  backend.

## Initial screens

1. Home: current tape, progress, transport controls and navigation.
2. Files: a simple list/browser suitable for touch, with Up/Down selection and
   automatic scrolling when more than six entries are present.
3. Filename: text field plus a Nokia-style 3x4 multi-tap keypad.
4. Settings: initially a placeholder; web-only settings may later include the
   preferred text-input method.

## Multi-tap keypad

The keypad follows classic mobile-phone behaviour rather than predictive T9.
Repeated presses cycle through the characters assigned to a key. A short pause,
pressing another key, or explicitly committing the pending character advances
the cursor.

Default mapping:

- `1`: `. , ? ! 1`
- `2`: `A B C 2`
- `3`: `D E F 3`
- `4`: `G H I 4`
- `5`: `J K L 5`
- `6`: `M N O 6`
- `7`: `P Q R S 7`
- `8`: `T U V 8`
- `9`: `W X Y Z 9`
- `0`: space, `0`, `_`, `-`
- `*`: backspace
- `#`: cycle input mode (`abc`, `ABC`, `123`)

The backend only receives the resulting filename/text. It must not know whether
that text came from the TFT keypad, the web keypad or a phone's native keyboard.

## Typography

Do not vendor the original ZX Spectrum ROM font without a clear redistribution
basis. The renderer should use an openly licensed 8x8-style font asset. BESCII
is a suitable prototype font (CC0 1.0) while keeping the font asset replaceable
if a closer Spectrum-style open font is selected later.
