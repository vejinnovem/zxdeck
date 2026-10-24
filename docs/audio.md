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

## Two different output controls

ZX Deck deliberately separates the generated tape-signal level from the USB
audio adapter's own playback mixer. They are two stages in the same signal
path, so a high value in one stage does not compensate for an unexpectedly low
value in the other.

`TAPE SIGNAL` controls the amplitude of the generated unsigned 8-bit tape PCM
before it reaches ALSA. The saved range is 0-100%. New or older state files
without a saved value start at a conservative 25%; 100% reproduces the original
generated PCM amplitude. The `-`, `MUTE` and `+` controls change it in 5% steps,
and holding `-` or `+` repeats the adjustment. A change also affects an
already-running playback worker, normally within one PCM buffer interval.

`CARD OUTPUT` controls the selected playback device's ALSA hardware mixer. ZX
Deck looks for a usable playback-volume control, preferring controls named
`Speaker`, `Headphone`, `PCM` and `Master`. If the adapter exposes no suitable
mixer, Settings shows `N/A` and the card-level screen explains that there is no
playback mixer to adjust.

This distinction matters for Spectrum loading: a USB dongle can receive a
full-strength generated tape waveform while its ALSA `Speaker` control is still
set too low for the Spectrum EAR input. The Settings screen therefore shows the
actual card-mixer percentage separately from the generated tape percentage.

Neither percentage is a calibrated electrical voltage at the Spectrum EAR
input. Different USB adapters can produce very different analog levels, so the
lowest reliable combination should be used rather than treating either 100% as
a universal electrical target.

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
