# Application architecture

## One backend, two frontends

`zxdeck.core.Backend` is the single owner of public application state. The
future local touchscreen UI and web UI both dispatch commands to this backend
and subscribe to immutable `DeckState` snapshots.

Tape parsing/generation, audio input/output and storage will be implemented as
backend services and command handlers. They must not be implemented in either
frontend.

```text
touch frontend ─┐
                ├─ commands -> Backend -> tape/audio/storage
web frontend ───┘                  |
                   state snapshots ┘
```

The command/state boundary is deliberately transport-neutral. It can initially
be used in one process on the Pi and later exposed through an HTTP/WebSocket or
local IPC adapter without moving domain logic into the web layer.

## Optional display

The core package does not import `spidev`, `lgpio` or the hardware drivers.
Raspberry Pi modules load those dependencies lazily only when an enabled TFT or
touchscreen is instantiated. A configuration with both devices disabled is
valid and must remain the default example.

Failure or absence of the TFT must never prevent the backend or web frontend
from starting. The local frontend will be an adapter under
`zxdeck.frontends.touch`; it is not the backend.

## Repository boundaries

- `src/zxdeck/core/`: shared state and command dispatch.
- `src/zxdeck/hardware/`: reusable, optional GPIO/SPI support.
- `tools/`: manual hardware diagnostics, not importable application modules.
- `docs/hardware/`: wiring, OS preparation and reproduction instructions.
- `config/`: examples and explicitly named tested hardware profiles.
- runtime state: outside the checkout, normally under `~/.local/state/zxdeck`
  during development or `/var/lib/zxdeck` for a system service.

