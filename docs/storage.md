# Tape-image storage and indexing

## One filesystem interface

ZX Deck always reads tape images from a directory. The physical medium is an
operating-system concern:

- the system microSD uses a directory such as
  `~/.local/share/zxdeck/tapes`;
- a USB disk may be mounted at `/mnt/zxdeck`;
- a future SPI microSD socket needs a kernel/device-tree driver and is then
  mounted at the same kind of path.

The application must not implement an SD block driver or select a raw SPI chip.
This keeps storage logic identical across all three options and lets Linux
handle filesystems, recovery and safe unmounting.

On the current prototype, SPI0 already uses both hardware chip selects: CE0 for
the LCD and CE1 for touch. A future SD socket therefore cannot simply become a
third SPI0 device. Raspberry Pi Zero exposes SPI1 with separate pins and three
chip selects, so SPI1 plus an appropriate kernel/device-tree overlay is the
likely direction, but wiring and driver support must be verified after the
socket is physically available. Do not reserve pins or edit boot overlays yet.

Reference: [official Raspberry Pi SPI bus and pin mapping](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#serial-peripheral-interface-spi).

`config/application.zxdeck-pi-zero.toml` contains the current defaults. A
removable-card configuration can use:

```toml
[storage]
path = "/mnt/zxdeck/tapes"
browse_root = "/mnt/zxdeck"
require_mount = true
mount_path = "/mnt/zxdeck"
recursive = true
extensions = [".tap", ".tzx", ".pzx"]
```

`require_mount` prevents a missing removable card from silently redirecting
writes into an ordinary empty directory on the system card. The UI-selected
subdirectory is stored outside the checkout in
`~/.local/state/zxdeck/storage-path` and survives Git updates.

## Touch directory picker

Settings contains a directory picker with the same large-target design as the
tape list. It shows directories only, supports parent/up/down navigation and
cannot move above `browse_root`. `USE` selects the current directory. This
allows a path to be chosen without typing Linux paths on the 240x320 screen.

## Network file transfer

For a home installation, the tape library can optionally be shared over SMB so
TAP/TZX/PZX files can be copied from another computer without SSH or removing
the Raspberry Pi microSD card. SMB is not required by ZX Deck itself and should
remain an opt-in operating-system service.

See `docs/network-file-transfer.md` for a Samba example. The share is intended
for a trusted LAN/Wi-Fi network only; do not port-forward SMB or expose TCP 445
or 139 directly to the Internet.

## Large libraries

Tape files do not need physical A-Z directories. `TapeLibrary` scans filenames
once with `os.scandir`/`os.walk`, filters known extensions and keeps a sorted
in-memory index. Search and A-Z grouping then operate on that index without
touching storage again. Physical subdirectories remain supported when they are
useful to the owner, but the UI grouping stays virtual.

The current touch search uses the same classic multi-tap editor as filename
entry. An empty query restores the full library.

## Snapshot files are not tapes

`.z80` and `.sna` files are emulator snapshots containing RAM and CPU state,
not tape images. They cannot reproduce the original tape signal or its custom
loader and are intentionally excluded from the playable library. Historical
tools can wrap a snapshot in a special loader tape, but that generated tape is
not the original recording and is unsuitable as the primary compatibility
test corpus. Use `.tap`, `.tzx` or `.pzx` files for zxdeck audio tests.

References: [World of Spectrum Z80 format](https://worldofspectrum.org/faq/reference/z80format.htm)
and [TZX format specification](https://www.worldofspectrum.net/TZXformat.html).

Before copying a mixed archive to the device, build a strict library with:

```bash
PYTHONPATH=src .venv/bin/python tools/filter_tape_library.py SOURCE DESTINATION
```

The filter validates TAP block boundaries and XOR checksums, recognises TZX/PZX
headers, repairs a `.tzx` filename when its content is actually TAP, excludes
disk/snapshot formats, and writes `_zxdeck-filter-report.tsv`. Files with valid
block structure but bad TAP checksums stay in the report unless
`--include-checksum-warnings` is explicitly requested.
