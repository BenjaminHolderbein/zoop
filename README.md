# zoop

An unofficial CLI for [Blip](https://blip.net): send files through the genuine
Blip app from the command line, or, via the bundled Claude Code plugin, by just
saying **"zoop this to my mac."** (It still answers to *"blip this,"* too.)

Blip has no public API or CLI of its own. This project drives the **genuine Blip
app** through the same local interfaces it already uses — so the polished receive
experience on the other device is fully preserved. No UI is automated.

Both steps below read your friendly device/contact names live from Blip's local
`state.dat` (a protobuf): a name like `MacBook Pro` or a contact like `Ben` maps
to its peer id `user_id:device_id`.

> Peer ids are **not** hardcoded — they're read live from `state.dat`, so they
> survive re-pairing devices.

## How it works

The transfer is triggered differently per OS, because Blip exposes a different
local interface on each:

* **Windows / Linux** — the desktop binary accepts a launcher flag set:
  ```
  blip --peer <user_id>:<device_id> --file <path> [--file <path> ...]
  ```
  Blip is single-instance, so a second invocation forwards these args to the
  running app, which creates the transfer.
* **macOS** — the app has no such CLI. Its background core instead serves a local
  [DRPC](https://github.com/storj/drpc) socket (in Blip's App Group container)
  with a `Dispatch` method. A send is three dispatched protobuf events —
  `TransferCreateRequested` → `TransferAddContentRequested` →
  `TransferInviteRequested` — which is exactly what the app's own UI does. This
  is implemented in pure stdlib (no protobuf/grpc deps); see
  [`src/zoop/macsend.py`](src/zoop/macsend.py).

## Platform support

| OS      | Status        | Notes |
|---------|---------------|-------|
| Windows | ✅ Verified   | MSIX/Store build; `--peer`/`--file` launcher. |
| macOS   | ✅ Verified   | `net.blip.macos` build; native DRPC socket. |
| Linux   | 🧪 Best-effort | Candidate paths shipped; **PRs welcome**. |

Per-OS specifics live in one file: [`src/zoop/platforms.py`](src/zoop/platforms.py).
If Blip is installed somewhere unexpected, override discovery with the
`BLIP_STATE` (path to `state.dat`), `BLIP_BIN` (Blip binary, win/linux), or
`BLIP_SOCK` (DRPC socket, macOS) environment variables — no code change needed.

## Install

### As a Claude Code plugin (natural language)

```
/plugin marketplace add BenjaminHolderbein/zoop
/plugin install zoop@zoop
```

Then in any conversation: *"zoop this file to my iPad"*, *"send report.pdf to my
mac with blip"*. (Requires Python 3.8+ on PATH.)

### As a standalone CLI

```
pipx install git+https://github.com/BenjaminHolderbein/zoop
# or, from a checkout:
pip install .
```

…or run with zero install from a checkout:

```
python zoop.py list
```

### Other harnesses (Codex, Cursor, …)

The Claude Code plugin bundles everything; other agents use the same engine via a
small per-harness shim. Install the CLI once (`pipx install
git+https://github.com/BenjaminHolderbein/zoop`), then drop in the shim for
your tool:

- **Codex** — an Agent Skill: [`integrations/codex`](integrations/codex)
- **Cursor** — a `.cursor/rules` rule: [`integrations/cursor`](integrations/cursor)

The shared CLI contract every shim builds on (and how to add your own harness)
is documented in [`integrations/`](integrations/README.md).

## Usage

```bash
zoop list                                  # show your devices + contacts + peer ids
zoop send --to "MacBook Pro" report.pdf    # send to one of your devices
zoop send --to "Ben" report.pdf            # send to a contact by name
zoop send --to mac a.png b.png             # partial name, multiple files
zoop send --to mac report.pdf --dry-run    # print what would be sent only
zoop doctor                                # diagnostics (paths, transport)
```

(`python zoop.py <args>` works identically without installing.)

## Limitations

- **Contacts must already be known locally.** You can send to your own devices
  and to any *contact* you've already transferred with (they appear in
  `state.dat`). Brand-new people you've never exchanged a file with are resolved
  server-side by Blip and aren't available from local data — do one transfer with
  them through the app first, then they're addressable by name here.
- Rides **undocumented** local interfaces (the launcher flags on Windows/Linux,
  the DRPC `Dispatch` events on macOS); a future Blip update could change either.
  `zoop doctor` plus the notes in `platforms.py` / `macsend.py` are the
  place to start if behavior changes.

## Contributing (esp. macOS / Linux)

1. Install + sign in to Blip.
2. Run `python zoop.py doctor` and see which candidate paths are found.
3. If `state.dat` or the binary isn't found, add the correct path to
   `state_dat_candidates()` / `launcher_prefix()` in
   [`src/zoop/platforms.py`](src/zoop/platforms.py).
4. Verify with `... send --to <device> <file> --dry-run`, then a real send.
5. Open a PR updating the support table above.

## Legal / interop note

This is interoperability tooling for files you send from your own account using
the app as intended. It reads your local app state and drives the official app
through its own local interfaces (the launcher flags, or — on macOS — the local
DRPC socket the app already runs). It does not touch Blip's network protocol,
bypass any protection, or talk to Blip's servers; the genuine app performs every
transfer. Not affiliated with Blip Studio Inc.

## License

MIT — see [LICENSE](LICENSE).
