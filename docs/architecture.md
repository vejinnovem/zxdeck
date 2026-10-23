# Application architecture

## One backend, two frontends

`zxdeck.core.Backend` is the single owner of public application state. The
future local touchscreen UI and web UI both dispatch commands to this backend
and subscribe to immutable `DeckState` snapshots.

Storage indexing and tape playback already live in reusable modules outside the
touch renderer. They will move behind shared backend command handlers before a
second frontend is added. Audio capture is not implemented yet.

```text
touch frontend ─┐
                ├─ commands -> Backend -> tape/audio/storage
web frontend ───┘                  |
                   state snapshots ┘
```

The command/state boundary is deliberately transport-neutral. It can initially
be used in one process on the Pi and later exposed through an HTTP/WebSocket or
local IPC adapter without moving domain logic into the web layer.

## Real-time audio boundary

The playback engine does not run in the touchscreen event loop. A disposable
worker process owns `aplay`, decodes the tape stream and feeds it through a
bounded 32 KiB PCM buffer. The UI exchanges only start/stop requests and small
status events with that process. Capture should follow the same isolation rule.

An audio callback must never render with Pillow, write to the TFT over SPI,
scan storage or parse tape files. Playback currently uses blocking ALSA writes
instead of a callback; parsing and PCM generation happen in the isolated
worker. Future capture tests must explicitly detect overruns and dropped
samples.

The touch UI remains event-driven. Static screens are not refreshed on a timer;
the filename cursor is the only periodic animation and is only active while
editing a name, when tape audio is not running.

## Optional display

The core package does not import `spidev`, `lgpio` or the hardware drivers.
Raspberry Pi modules load those dependencies lazily only when an enabled TFT or
touchscreen is instantiated. A configuration with both devices disabled is
valid and must remain the default example.

Failure or absence of the TFT must never prevent the backend or web frontend
from starting. The local frontend will be an adapter under
`zxdeck.frontends.touch`; it is not the backend.

## OS, networking and update adapters

Wi-Fi control, IP discovery, SMB, the future web server and software updates are
operating-system integration concerns. They must not be implemented inside the
tape, audio or storage domain logic.

The current touch application only consumes a small read-only system helper to
show the current IPv4 address. Future Wi-Fi management should wrap
NetworkManager rather than reimplementing wireless configuration. The web
frontend must be independently switchable; when disabled it must not leave a
listening HTTP/WebSocket socket behind.

Updates should be a separate adapter around Git. It may check for a newer
revision automatically, but installing an update requires explicit user action.
The updater must refuse unsafe updates from a dirty checkout and use a
fast-forward-only operation rather than silently overwriting local changes.

Network-facing services such as SMB and the web UI are intended for a trusted
LAN/Wi-Fi network. ZX Deck must not automatically configure router port
forwarding, expose SMB to the Internet or otherwise broaden its network attack
surface without an explicit administrator action outside the application.

## Repository boundaries

- `src/zxdeck/core/`: shared state and command dispatch.
- `src/zxdeck/hardware/`: reusable, optional GPIO/SPI support.
- `src/zxdeck/system/`: small operating-system integration helpers that are not
  part of tape/audio domain logic.
- `tools/`: manual hardware diagnostics, not importable application modules.
- `docs/hardware/`: wiring, OS preparation and reproduction instructions.
- `config/`: examples and explicitly named tested hardware profiles.
- runtime state: outside the checkout, normally under `~/.local/state/zxdeck`
  during development or `/var/lib/zxdeck` for a system service.
