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
are available, but the tape engine and full user interfaces are not implemented
yet.

See:

- `docs/architecture.md` for application boundaries;
- `docs/hardware/display.md` for wiring and verified parameters;
- `docs/hardware/raspberry-pi-setup.md` for clean-system setup.

## Development checks

The core and configuration tests need no Raspberry Pi libraries:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The Raspberry Pi diagnostic tools are run from a virtual environment created
with access to system packages; see the hardware setup guide.
