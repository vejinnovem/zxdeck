# zxdeck

Portable digital tape recorder/player for ZX Spectrum computers, built around
a Raspberry Pi. Playback and recording are both planned.

> **Transparency:** ZX Deck is a vibe-coded project. I am not a programmer;
> the project is being built with AI assistance, with changes checked by
> automated tests and real-hardware testing.
>
> **Use at your own risk:** ZX Deck is a hobby project provided as-is, without
> warranty. Software, wiring, GPIO, audio connections and hardware instructions
> should be verified before use. The author does not guarantee suitability for
> any particular hardware or configuration.

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

A first 240x320 touchscreen UI is present. It renders Home, Files, Search,
Filename, scrollable Settings, Output Level, Directory and Power screens from
hardware-independent code, includes a classic 3x4 multi-tap phone keypad for
text entry, and can be previewed as PNGs or run interactively on the tested
TFT/touch hardware. The device-facing Settings screen also shows the current
IPv4 address for SSH and diagnostics. File-list Up/Down supports hold-to-repeat
and changes to whole-letter-group jumps during a longer hold.

The file browser uses the configured, validated tape library; built-in
filenames are only available through the explicit `--mock-files` development
option. PLAY decodes TAP plus the common TZX standard, turbo, pure-tone,
pulse-sequence, pure-data and direct-recording blocks in an isolated process
and streams unsigned 8-bit mono PCM to the ALSA playback device selected in the
application configuration. Playback now calculates total generated-signal
duration and reports progress back to the Home screen. The generated signal has
a persistent 0-100% software output-level control with large `-`, `MUTE` and
`+` targets; 25% is the conservative default for state files that do not yet
contain a saved level. Rare generalized, CSW and control-flow TZX blocks fail
visibly instead of producing an incorrect signal. Recording and the web
frontend are not implemented yet.

See:

- `docs/architecture.md` for application boundaries;
- `docs/ui-prototype.md` for the current UI rules and keypad behaviour;
- `docs/storage.md` for directory selection, removable media and indexing;
- `docs/audio.md` for ALSA selection, playback progress and output level;
- `docs/network.md` for Wi-Fi, IP display, future Web UI and update rules;
- `docs/network-file-transfer.md` for optional SMB file transfer on a trusted LAN;
- `docs/hardware/display.md` for wiring and verified parameters;
- `docs/hardware/raspberry-pi-setup.md` for clean-system setup.

## Problems and feedback

Please use [GitHub Issues](https://github.com/vejinnovem/zxdeck/issues) for bugs,
hardware compatibility reports, installation problems and feature requests.
For a bug, include the ZX Deck commit/version, Raspberry Pi model, Raspberry Pi
OS version, ZX Spectrum model, display/touch hardware, USB audio device, steps
to reproduce the problem and relevant logs where possible. Issue templates are
provided to make reports easier to diagnose.

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
