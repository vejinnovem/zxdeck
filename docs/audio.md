# Audio-device configuration

Playback device selection is separate from GPIO/SPI wiring in the application
configuration:

```toml
[audio]
capture_device = "default"
playback_device = "default"
```

When the USB interface is connected, list ALSA names with `arecord -L` and
`aplay -L`. Prefer a stable name such as `plughw:CARD=Device,DEV=0` over a
numeric index such as `hw:1,0`, because card numbers may change between boots.

The touchscreen Settings screen has separate `PLAYBACK` and `CAPTURE` pickers.
Opening either picker refreshes the physical ALSA device list. A selection is
stored in `~/.local/state/zxdeck/audio.json`, outside the checkout, and
overrides the TOML default on later boots. A newly selected playback endpoint
is used by the next PLAY action; no service restart is required.

## Output level

`OUTPUT LEVEL` controls the amplitude of the generated unsigned 8-bit tape
signal before it reaches ALSA. It is intentionally independent of the USB
adapter's hardware mixer so it works even with simple USB audio dongles that do
not expose a useful playback-volume control.

The saved range is 0-100%. New or older state files without a saved value start
at a conservative 25%; 100% reproduces the original generated PCM amplitude.
The `-`, `MUTE` and `+` controls change level in 5% steps, and holding `-` or `+`
repeats the adjustment. A change also affects an already-running playback
worker, normally within one PCM buffer interval.

This is a software signal-level control, not a calibrated electrical limit for
the Spectrum EAR input. Different USB adapters can produce very different
analog voltages. A future hardware guide should still define a measured safe
attenuator/calibration procedure before treating 100% as universally safe.

## Playback timing and progress

PLAY starts a disposable worker process which opens exactly the configured
playback device through `aplay`. Before playback, the worker calculates the
exact generated PCM sample count directly from the TAP/TZX pulse stream without
rendering a temporary WAV file. That sample count becomes the duration shown on
the Home screen.

Playback then decodes the selected TAP/TZX stream and writes 44.1 kHz unsigned
8-bit mono PCM through a bounded 32 KiB buffer. Each completed buffer reports
its generated sample position to the UI, so the `00:00`, total-time readout and
progress bar advance during playback. The position has buffer-sized granularity
rather than pretending to be sample-perfect at the physical analog output.

STOP signals that worker and waits briefly for ALSA to close. A missing device
or an unsupported TZX block is reported on the Home screen.

Capture/recording is not implemented yet. It must use the configured capture
device and remain isolated from TFT rendering and storage scans as described in
`architecture.md`.
