# ZX Deck UI prototype

The UI began as a hardware-independent prototype. It now indexes the configured
storage and starts isolated TAP/TZX playback; mock filenames are available only
through an explicit development flag.

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

1. Home: current tape, progress, transport controls and navigation. Long tape
   names pause, scroll to the end, pause again and scroll back. Only the small
   title strip is refreshed during this animation.
2. Files: a simple list/browser suitable for touch, with Up/Down selection,
   automatic scrolling and multi-tap search.
3. Filename: text field plus a Nokia-style 3x4 multi-tap keypad. Entering this
   screen always stops transport; only an explicit REC press may start mock
   recording.
4. Settings: tape-directory selection and a confirmed system Power Off action.
5. Directory picker: directory-only Linux navigation constrained by the
   configured browse root.

## Multi-tap keypad

The keypad follows classic mobile-phone behaviour rather than predictive T9.
Repeated presses cycle through the characters assigned to a key. A short pause,
pressing another key, or explicitly committing the pending character advances
the cursor.

While a multi-tap character is pending, the filename cursor is hidden. After
the timeout commits that character, the cursor appears after it and blinks.
Touch targets invert immediately on press, before the resulting screen is
rendered, so physical input acknowledgment is distinct from action latency.

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

## Safe shutdown

Power Off is deliberately a two-screen action: Settings opens a confirmation
screen, and only the red confirmation target requests system shutdown. The
hardware adapter must redraw a `SHUTTING DOWN` screen before invoking the
privileged operating-system action. The development demo ignores the request
unless `--allow-poweroff` was explicitly supplied.

The TFT backlight is not currently software-controlled, so it is not a reliable
shutdown-complete indicator. After confirmation, wait for the Raspberry Pi's
green ACT LED to stop showing storage activity before removing power.

## Typography

Do not vendor the original ZX Spectrum ROM font without a clear redistribution
basis. The renderer should use an openly licensed 8x8-style font asset. BESCII
is a suitable prototype font (CC0 1.0) while keeping the font asset replaceable
if a closer Spectrum-style open font is selected later.
