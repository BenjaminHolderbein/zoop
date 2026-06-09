---
name: blip-send
description: >-
  Send files to one of the user's own devices, or to a known contact, through the
  Blip file-transfer app. Use this whenever the user asks to "blip" a file or
  send/share a file via Blip, e.g. "blip this to my mac", "send report.pdf to my
  iphone with blip", "blip this to nick". Resolves a friendly device name or
  contact name to a Blip peer id and dispatches the transfer through the genuine
  Blip app (no UI driving). Recipients must already exist in the local Blip state
  (own paired devices, or contacts you've previously transferred with).
---

# Blip a file to one of my devices

This skill sends file(s) to one of the user's own Blip-paired devices (Mac,
iPhone, iPad, PC, etc.) or to a known contact, using a bundled cross-platform
CLI. Blip must be installed and signed in, and ideally already running.

## How to run it

Use the Python launcher bundled with this plugin. Use `python3` on macOS/Linux
and `python` on Windows (where `python3` may launch the Store). The examples
below use `python3`. All commands are run from any directory.

1. **Identify the file(s)** the user means (the file they referenced or attached).
   Resolve to concrete paths. If unclear, ask which file.

2. **Identify the recipient** from the user's phrasing — one of their own devices
   ("my mac" -> "MacBook Pro", "my phone" -> "iPhone") or a contact by name
   ("nick", "Ben"). If you are unsure who/what they mean, list known recipients
   first (the output shows your devices and your contacts):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/blip_send.py" list
   ```

3. **Send**, passing the device or contact name to `--to` (partial,
   case-insensitive names work, e.g. `--to mac` or `--to ben`):

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/blip_send.py" send --to "MacBook Pro" "/path/to/file"
   ```

   Multiple files: list them all after `send`. A full peer id
   (`user_id:device_id`) may be passed to `--to` instead of a name.

4. **Confirm** to the user that the transfer was dispatched and that they may
   need to accept it on the receiving device.

## Important behavior

- **Recipients must already be known locally.** You can send to the user's own
  devices and to any contact they've previously transferred with (these appear in
  `list`). If the requested person isn't known yet, tell the user that brand-new
  people aren't addressable from local data — they should do one transfer with
  that person through the Blip app first, then the contact becomes resolvable here.
- If `--to` matches no recipient, the CLI prints the known device and contact
  names; relay them and ask the user to pick.
- If the CLI reports it cannot find `state.dat` or the Blip binary, run
  `python3 "${CLAUDE_PLUGIN_ROOT}/blip_send.py" doctor` and share the output —
  on macOS/Linux the install paths may differ and can be set via the `BLIP_STATE`
  and `BLIP_BIN` environment variables.
- Use `--dry-run` (after `send`) to show the exact Blip command without sending,
  if the user wants to inspect it first.
