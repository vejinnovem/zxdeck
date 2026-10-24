# Recording behaviour

Recording is not implemented yet. The current REC action reports that explicitly; it does not open the capture device or write audio.

## Save-file location

User-created game saves live below the selected tape library in a dedicated `saves/` subtree. The ordinary FILES index deliberately prunes that subtree so save slots do not get mixed into the game/program list. The FIND screen exposes a separate **SAVES** shortcut which lists supported save files (`.wav`, `.tap`, `.tzx`, `.pzx`).

This directory convention is already part of the UI even before capture is implemented, so the later REC workflow can use it without reorganising existing libraries.

## Signal-phase feedback

During PLAY, the progress track should also act as a tape-signal indicator inspired by the ZX Spectrum loading border:

- pilot/tone/sync pulses: alternating red and blue,
- encoded/direct data: alternating yellow and blue,
- pause/silence: ordinary neutral progress styling.

The elapsed part of the track is bright and the remaining part dimmed, so it still works as a progress bar. The stripe pattern may shift slowly on each small progress refresh to suggest the moving Spectrum border without trying to reproduce the actual hundreds-of-Hz EAR transitions on the TFT.

Playback knows the phase directly from the tape-event generator, so this indication does not need to infer anything from audio.

During REC there is no duration-based progress bar because recording length is unknown. Instead the REC control should blink while capture is active. Once real-time input pulse classification exists, that same button can communicate the received phase: red/blue for detected pilot/tone and yellow/blue for detected data. When no valid tape signal is detected it should fall back to a normal recording blink rather than claiming a phase.

## Intended workflow

ZX Deck should treat recording as an audio-capture operation first and conversion as a separate step.

- **NEW -> REC** records a new WAV in the selected library's `saves/` directory. WAV is the canonical writable recording format because it preserves exactly what came from the Spectrum MIC output.
- **Existing WAV -> REC** asks for confirmation before replacing the file. The default action must be Cancel. A future optional mode may append or create a timestamped sibling instead of overwriting.
- **Existing TAP/TZX -> REC** must never silently overwrite the structured tape image with captured audio. The UI should offer to record a new WAV in `saves/` using the same base name (for example `GAME.TZX` -> `saves/GAME-save.wav`) or ask for a new name.
- Automatic WAV -> TAP/TZX decoding may be offered after recording when decoding succeeds, but the original WAV should be kept unless the user explicitly deletes it. Conversion is not reliable enough to make TAP/TZX the only writable representation.

This behaviour is particularly important for games that save progress to tape. Repeated saves should be quick: FIND -> SAVES -> select an existing save WAV -> REC -> confirm replacement. Structured program TAP/TZX files remain protected.

## Safety

Starting REC while PLAY is active must stop playback first. Overwriting any existing file requires an explicit confirmation screen showing the target filename. Recording failures must leave the previous file intact; capture should write to a temporary file and atomically replace the target only after a successful stop/close.
