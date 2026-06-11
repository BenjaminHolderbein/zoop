---
name: zoop
description: >-
  Send files to one of the user's own devices, or to a known contact, through the
  Blip file-transfer app. Use this whenever the user asks to "zoop" or "blip" a
  file or to send/share a file via Blip, e.g. "zoop this to my mac", "blip this to
  my iphone", "send report.pdf to my iphone with blip", "zoop this to nick".
  Resolves a friendly device or contact name to a Blip peer id and sends through
  the genuine Blip app (no UI driving).
when_to_use: >-
  The user wants to send/share a local file to one of their own devices or a known
  contact via Blip ("zoop this to my mac", "blip this to my iPhone", "send X with
  blip").
---

# Zoop a file to a device or contact

Sends file(s) to one of the user's Blip-paired devices (Mac, iPhone, iPad, PC,
…) or to a known contact, using the `zoop` CLI. Blip must be installed and
signed in, and ideally already running.

## Prerequisite

The `zoop` CLI must be on PATH:

```
pipx install git+https://github.com/BenjaminHolderbein/zoop
```

Verify with `zoop doctor`. (If it isn't installed, install it, or run the
checked-out launcher instead: `python zoop.py …` on Windows, `python3
zoop.py …` on macOS/Linux.)

## How to run it

1. **Identify the file(s)** the user means (referenced or attached). Resolve to
   concrete paths. If unclear, ask which file.

2. **Identify the recipient** from the user's phrasing — one of their own devices
   ("my mac" -> "MacBook Pro", "my phone" -> "iPhone") or a contact by name
   ("nick", "Ben"). If unsure, list known recipients first:

   ```
   zoop list
   ```

3. **Send**, passing the device or contact name to `--to` (partial,
   case-insensitive names work, e.g. `--to mac` or `--to ben`):

   ```
   zoop send --to "MacBook Pro" "/path/to/file"
   ```

   Multiple files: list them all after `send`. A full peer id
   (`user_id:device_id`) may be passed to `--to` instead of a name.

4. **Confirm** to the user that the transfer was sent and that they may need to
   accept it on the receiving device.

## Important behavior

- **Recipients must already be known locally.** You can send to the user's own
  devices and to any contact they've previously transferred with (these appear in
  `list`). If the requested person isn't known yet, tell the user that brand-new
  people aren't addressable from local data — they should do one transfer with
  that person through the Blip app first, then the contact becomes resolvable here.
- If `--to` matches no recipient, the CLI prints the known device and contact
  names; relay them and ask the user to pick.
- If the CLI can't find Blip's state or transport, run `zoop doctor` and
  share the output. Paths can be overridden via `BLIP_STATE` (state.dat),
  `BLIP_BIN` (Blip binary, Windows/Linux), or `BLIP_SOCK` (DRPC socket, macOS).
- Use `--dry-run` (after `send`) to show what would be sent without sending.
