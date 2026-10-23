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

PLAY starts a disposable worker process which opens exactly the configured
playback device through `aplay`. It decodes the selected TAP/TZX stream and
writes 44.1 kHz unsigned 8-bit mono PCM through a bounded 32 KiB buffer. STOP
signals that worker and waits briefly for ALSA to close. A missing device or an
unsupported TZX block is reported on the Home screen.

Capture/recording is not implemented yet. It must use the configured capture
device and remain isolated from TFT rendering and storage scans as described in
`architecture.md`.
