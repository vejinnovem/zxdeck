# zxdeck

Portable digital tape recorder/player for ZX Spectrum computers, built around
a Raspberry Pi. Playback and recording are both planned.

> **Transparency:** ZX Deck is a vibe-coded project. I am not a programmer;
> the project is being built with AI assistance, with changes checked by
> automated tests and real-hardware testing.

## Recommended platform

The currently recommended and verified base system is **32-bit Raspberry Pi OS
13 (Trixie)** on a **Raspberry Pi Zero W**. This is the platform used for the
real-hardware development and testing described in this repository. Other
Raspberry Pi models or OS releases may work, but they are not the primary test
target at this stage.

The application is designed around one authoritative backend/state model with
two optional frontends:

- a local 240x320 touchscreen interface;
- a web interface for another computer or phone.

Neither frontend owns tape, audio or storage logic. The TFT is optional: the
backend and future web frontend must remain usable without Raspberry Pi display
dependencies.

## Current status

The tested ILI9341-compatible LCD and XPT2046 touchscreen support has been
extracted into reusable modules. Standalone diagnostic and calibration tools
are available.

A first 240x320 touchscreen UI prototype is also present. It renders Home,
Files, Search, Filename, Settings, Directory and Power screens from
hardware-independent code, includes a classic 3x4 multi-tap phone keypad for
text entry, and can be previewed as PNGs or run interactively on the tested
TFT/touch hardware. The file browser uses the configured, validated tape
library; built-in filenames are only available through the explicit
`--mock-files` development option. PLAY now decodes TAP plus the common TZX
standard, turbo, pure-tone, pulse-sequence, pure-data and direct-recording
blocks in an isolated process and streams unsigned 8-bit mono PCM to the ALSA
playback device selected in the application configuration. Rare generalized,
CSW and control-flow TZX blocks fail visibly instead of producing an incorrect
signal. Recording and the web frontend are not implemented yet.

See:

- `docs/architecture.md` for application boundaries;
- `docs/ui-prototype.md` for the current UI rules and keypad behaviour;
- `docs/storage.md` for directory selection, removable media and indexing;
- `docs/audio.md` for stable ALSA device selection;
- `docs/hardware/display.md` for wiring and verified parameters;
- `docs/hardware/raspberry-pi-setup.md` for clean-system setup.

## Development checks

The core, configuration and keypad tests need no Raspberry Pi libraries:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Generate hardware-free UI previews with:

```bash
PYTHONPATH=src python3 tools/ui_preview.py
```

On the configured Raspberry Pi prototype, run the interactive UI with:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_touch_demo.py
```

The Raspberry Pi tools use a virtual environment created with access to system
packages; see the hardware setup guide.
