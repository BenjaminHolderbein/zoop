# Integrations

`zoop` is built as an **engine + thin per-harness shims**. The engine is the
cross-platform `zoop` CLI (in [`../src/zoop`](../src/zoop)); each AI
coding agent ("harness") just needs a small file telling it *when* to run that
CLI and *how*. No harness needs the engine reimplemented, and there is no MCP
server to run — everything goes through the CLI.

```
            ┌─────────────────────────────┐
            │  zoop CLI (the engine) │  reads state.dat, drives Blip
            │  list · send · doctor        │  (launcher on win/linux,
            └─────────────┬───────────────┘   DRPC socket on macOS)
                          │  stable contract (below)
        ┌─────────────────┼──────────────────┐
        │                 │                  │
   Claude Code         Codex              Cursor
   (skill + plugin)   (skill)            (.mdc rule)
   ../skills/         codex/             cursor/
```

## Per-harness setup

| Harness     | Mechanism                          | Setup | Folder |
|-------------|------------------------------------|-------|--------|
| Claude Code | Skill, bundled in a plugin         | `/plugin install` — zero-install, the engine ships with the plugin | [`../skills`](../skills) + [`../.claude-plugin`](../.claude-plugin) |
| Codex       | Agent Skill (`SKILL.md`)           | `pip install` the engine, drop the skill in `~/.codex/skills/` | [`codex/`](codex) |
| Cursor      | Project Rule (`.mdc`)              | `pip install` the engine, drop the rule in `.cursor/rules/` | [`cursor/`](cursor) |

Claude Code is the only harness with a fetch-and-bundle install mechanism we can
target, so it gets the zero-install experience. For every other harness the user
installs the engine once with pip and copies in the shim — that's the standard
flow those tools expect anyway.

## Installing the engine (Codex, Cursor, anything non-Claude)

```
pipx install git+https://github.com/BenjaminHolderbein/zoop
# verify:
zoop doctor
```

`zoop` is then on PATH on Windows, macOS, and Linux. (macOS uses Blip's
local DRPC socket internally; same CLI, no extra setup.)

---

## The CLI contract (stable integration surface)

Build any harness shim against this. These commands, their output shape, and the
env overrides are the supported surface; internal modules are not.

### `zoop list [--json]`

Human output by default. `--json` emits:

```json
{
  "self": {
    "user_id": "…", "email": "…|null", "name": "…|null", "is_self": true,
    "devices": [{ "id": "…", "name": "MacBook Pro", "kind": 4, "peer": "<user_id>:<device_id>" }]
  },
  "contacts": [
    { "user_id": "…", "email": "…", "name": "Ben", "is_self": false,
      "devices": [{ "id": "…", "name": "iPad", "kind": 3, "peer": "<user_id>:<device_id>" }] }
  ]
}
```

`self` may be `null` if no signed-in account is found. `peer` is always
`user_id:device_id`.

### `zoop send --to <recipient> <file> [<file> …] [--dry-run]`

`<recipient>` may be:
- a device name (e.g. `"MacBook Pro"`, or partial/case-insensitive `mac`),
- a contact name (`Ben`) or contact email,
- or a full `user_id:device_id` peer id (passed straight through).

`--dry-run` prints what would be sent and sends nothing.

**Exit codes:** `0` on success. Non-zero with a human-readable message on:
file-not-found, no matching recipient (the message lists known recipients and
how to make a new person addressable), ambiguous recipient, or a transport
failure.

### `zoop doctor`

Prints platform, `state.dat` candidates, the active transport, and the resolved
account/devices/contacts. First thing to run when something doesn't work.

### Environment overrides

| Var          | Meaning                                   | Platforms   |
|--------------|-------------------------------------------|-------------|
| `BLIP_STATE` | Path to `state.dat`                       | all         |
| `BLIP_BIN`   | Path to the Blip binary (launcher send)   | win / linux |
| `BLIP_SOCK`  | Path to Blip's DRPC socket (socket send)  | macOS       |

### Invocation forms

- `zoop <args>` — when pip-installed (preferred for Codex/Cursor).
- `python zoop.py <args>` — zero-install from a checkout. Use `python` on
  Windows (where `python3` can launch the Store) and `python3` on macOS/Linux.

---

## Adding a new harness

1. Read the contract above — your shim only ever calls `zoop`.
2. Make the engine available (`pipx install …`).
3. Write the harness's idiomatic "skill/rule/instruction" file: trigger on
   phrases like *"blip this to my mac"*, then run `zoop list` to disambiguate
   and `zoop send --to <name> <files>` to send. Relay `send`'s output and
   note the user may need to accept on the receiving device.
4. Drop it in `integrations/<harness>/`, add a short README, and update the table
   above. PRs welcome.
