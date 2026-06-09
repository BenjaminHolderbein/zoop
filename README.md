# blip-cli

Send files through the [Blip](https://blip.net) file-transfer app from the
command line — and, via the bundled Claude Code plugin, by just saying
**"blip this to my mac."**

Blip has no public API or CLI of its own. But its desktop app (a Kotlin/Compose
app) ships a hidden launcher flag set, and this project uses it to drive the
**genuine Blip app** — so the polished receive experience on the other device is
fully preserved. Nothing is reimplemented and no UI is automated.

## How it works

The Blip desktop binary accepts:

```
blip --peer <user_id>:<device_id> --file <path> [--file <path> ...]
```

Blip is single-instance: a second invocation forwards these args to the
already-running app, which creates the transfer. This tool:

1. Reads Blip's local `state.dat` (a protobuf) to map a friendly name — one of
   your own devices (e.g. `MacBook Pro`) **or a contact** (e.g. `Ben`) — to its
   peer id `user_id:device_id`.
2. Invokes the Blip binary with `--peer` / `--file`.

> Peer ids are **not** hardcoded — they're read live from `state.dat`, so they
> survive re-pairing devices.

## Platform support

| OS      | Status        | Notes |
|---------|---------------|-------|
| Windows | ✅ Verified   | MSIX/Store build. |
| macOS   | 🧪 Best-effort | Candidate paths shipped; needs verification. |
| Linux   | 🧪 Best-effort | Candidate paths shipped; **PRs welcome**. |

Per-OS specifics live in one file: [`src/blip_cli/platforms.py`](src/blip_cli/platforms.py).
If Blip is installed somewhere unexpected, point the tool at it with the
`BLIP_STATE` (path to `state.dat`) and `BLIP_BIN` (path to the Blip binary)
environment variables — no code change needed.

## Install

### As a Claude Code plugin (natural language)

```
/plugin marketplace add BenjaminHolderbein/blip-cli
/plugin install blip@blip-cli
```

Then in any conversation: *"blip this file to my iPad"*, *"send report.pdf to my
mac with blip"*. (Requires Python 3.8+ on PATH.)

### As a standalone CLI

```
pipx install git+https://github.com/BenjaminHolderbein/blip-cli
# or, from a checkout:
pip install .
```

…or run with zero install from a checkout:

```
python blip_send.py list
```

## Usage

```bash
blip-send list                                  # show your devices + contacts + peer ids
blip-send send --to "MacBook Pro" report.pdf    # send to one of your devices
blip-send send --to "Ben" report.pdf            # send to a contact by name
blip-send send --to mac a.png b.png             # partial name, multiple files
blip-send send --to mac report.pdf --dry-run    # print the Blip command only
blip-send doctor                                # diagnostics (paths, launcher)
```

(`python blip_send.py <args>` works identically without installing.)

## Limitations

- **Contacts must already be known locally.** You can send to your own devices
  and to any *contact* you've already transferred with (they appear in
  `state.dat`). Brand-new people you've never exchanged a file with are resolved
  server-side by Blip and aren't available from local data — do one transfer with
  them through the app first, then they're addressable by name here.
- Rides an **undocumented** launcher flag set; a future Blip update could rename
  a flag. `blip-send doctor` plus the notes in `platforms.py` are the place to
  start if behavior changes.

## Contributing (esp. macOS / Linux)

1. Install + sign in to Blip.
2. Run `python blip_send.py doctor` and see which candidate paths are found.
3. If `state.dat` or the binary isn't found, add the correct path to
   `state_dat_candidates()` / `launcher_prefix()` in
   [`src/blip_cli/platforms.py`](src/blip_cli/platforms.py).
4. Verify with `... send --to <device> <file> --dry-run`, then a real send.
5. Open a PR updating the support table above.

## Legal / interop note

This is interoperability tooling for files you send from your own account using
the app as intended. It does not reimplement Blip's protocol, bypass any
protection, or reverse the wire format — it only reads your local app state and
invokes the official binary. Not affiliated with Blip Studio Inc.

## License

MIT — see [LICENSE](LICENSE).
