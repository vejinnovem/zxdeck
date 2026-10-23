# Audio-device configuration

Audio capture and playback are not implemented yet, but their device selection
is already separate from GPIO/SPI wiring in the application configuration:

```toml
[audio]
capture_device = "default"
playback_device = "default"
```

When the USB interface is connected, list ALSA names with `arecord -L` and
`aplay -L`. Prefer a stable name such as `plughw:CARD=Device,DEV=0` over a
numeric index such as `hw:1,0`, because card numbers may change between boots.

The future audio worker must open exactly the configured capture and playback
devices, report a clear error if either is absent, and remain isolated from TFT
rendering, storage scans and tape parsing as described in `architecture.md`.
