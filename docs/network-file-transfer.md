# Optional SMB file transfer

ZX Deck itself only needs a filesystem directory containing tape images. On a
trusted home network, Samba can optionally expose that directory as an SMB
share so files can be copied from Windows, macOS or Linux without SSH and
without removing the Raspberry Pi microSD card.

This is optional. Do not expose SMB directly to the Internet and do not create
router port forwards for TCP 445 or 139.

The examples below assume the normal ZX Deck library:

```text
/home/<user>/.local/share/zxdeck/tapes
```

Replace `<user>` with the Linux account that runs ZX Deck. If the application
uses another directory, share that directory instead.

## 1. Install Samba

```bash
sudo apt update
sudo apt install samba
```

Create the tape directory if it does not already exist:

```bash
mkdir -p ~/.local/share/zxdeck/tapes
```

## 2. Create an SMB password

Samba keeps its own authentication database. Add the existing Linux user:

```bash
sudo smbpasswd -a <user>
```

Choose a password for network file access. It does not have to be the Linux
login password.

## 3. Add the share

Edit `/etc/samba/smb.conf` and add a section like this at the end:

```ini
[zxdeck]
    path = /home/<user>/.local/share/zxdeck/tapes
    browseable = yes
    read only = no
    guest ok = no
    valid users = <user>
    create mask = 0664
    directory mask = 0775
```

Check the configuration before restarting Samba:

```bash
sudo testparm
sudo systemctl restart smbd
```

## 4. Connect from another computer

When the Raspberry Pi has address `192.168.1.84`, typical paths are:

```text
Windows:  \\192.168.1.84\zxdeck
macOS:    smb://192.168.1.84/zxdeck
Linux:    smb://192.168.1.84/zxdeck
```

If mDNS is working and the Raspberry Pi hostname is `zxdeck`,
`zxdeck.local` can be used in place of the numeric address. The touchscreen
Settings page should still be used as the reliable way to read the current IPv4
address.

Files copied into the configured tape directory become ordinary ZX Deck
library files. A later library-refresh feature may make newly copied files
appear immediately; until then, restarting or re-entering the relevant library
view may be necessary depending on the current application state.

## Security notes

- use SMB only on a trusted LAN/Wi-Fi network;
- keep `guest ok = no`;
- use a dedicated Samba password;
- do not expose SMB ports through the router;
- remove or disable the share if network file transfer is not wanted;
- the future ZX Deck installer should treat Samba as an optional component, not
  as a required dependency.

To disable the share while keeping Samba installed, remove or comment the
`[zxdeck]` section and restart `smbd`.
