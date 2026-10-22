# zxdeck

Portable digital tape recorder/player for ZX Spectrum computers, built around
a Raspberry Pi. Playback and recording are both planned.

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
Files, Filename and Settings screens from hardware-independent code, includes a
classic 3x4 multi-tap phone keypad for text entry, and can be previewed as PNGs
or run interactively on the tested TFT/touch hardware. Transport, file and save
actions currently operate on mock state only: tape parsing/generation, audio,
storage and the web frontend are not implemented yet.

See:

- `docs/architecture.md` for application boundaries;
- `docs/ui-prototype.md` for the current UI rules and keypad behaviour;
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

On the configured Raspberry Pi prototype, run the interactive mock UI with:

```bash
PYTHONPATH=src .venv/bin/python tools/ui_touch_demo.py
```

The Raspberry Pi tools use a virtual environment created with access to system
packages; see the hardware setup guide.
