# Recording behaviour

Recording is not implemented yet. The current REC action in the prototype only changes UI state; it does not open the capture device or write audio.

## Intended workflow

ZX Deck should treat recording as an audio-capture operation first and conversion as a separate step.

- **NEW -> REC** records a new WAV in the selected tape directory. WAV is the canonical writable recording format because it preserves exactly what came from the Spectrum MIC output.
- **Existing WAV -> REC** asks for confirmation before replacing the file. The default action must be Cancel. A future optional mode may append or create a timestamped sibling instead of overwriting.
- **Existing TAP/TZX -> REC** must never silently overwrite the structured tape image with captured audio. The UI should offer to record a new WAV using the same base name (for example `GAME.TZX` -> `GAME-save.wav`) or ask for a new name.
- Automatic WAV -> TAP/TZX decoding may be offered after recording when decoding succeeds, but the original WAV should be kept unless the user explicitly deletes it. Conversion is not reliable enough to make TAP/TZX the only writable representation.

This behaviour is particularly important for games that save progress to tape. Repeated saves should be quick: selecting an existing save WAV and pressing REC can replace it after one confirmation, while structured program TAP/TZX files remain protected.

## Safety

Starting REC while PLAY is active must stop playback first. Overwriting any existing file requires an explicit confirmation screen showing the target filename. Recording failures must leave the previous file intact; capture should write to a temporary file and atomically replace the target only after a successful stop/close.
