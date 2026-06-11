# Cursor integration

Send files via Blip from [Cursor](https://cursor.com) by natural language
("blip this to my mac").

Cursor uses **Project Rules** (`.mdc` files), so this is the engine + one rule
file in "Agent Requested" mode (the agent applies it when the description
matches).

## Install

1. **Engine** (one-time, on PATH):

   ```
   pipx install git+https://github.com/BenjaminHolderbein/zoop
   zoop doctor      # verify it finds Blip
   ```

2. **Rule** — copy the rule into the project where you want it (rules live under
   `.cursor/rules/`):

   ```
   mkdir -p /path/to/your/repo/.cursor/rules
   cp rules/zoop.mdc /path/to/your/repo/.cursor/rules/
   ```

   For a global rule available in every project, add it via Cursor Settings →
   Rules instead.

## Use

In Cursor's Agent: *"blip this file to my iPhone"*, *"send report.pdf to my mac
with blip"*. The rule activates on the description match and runs `zoop`.

## Notes

- The rule uses `alwaysApply: false` + a `description` ("Agent Requested" mode)
  so it only loads when relevant. Set `alwaysApply: true` if you want it always
  in context.
- Optionally add a `.cursor/commands/blip.md` for an explicit `/blip` command.
- macOS works with no extra setup (engine uses Blip's local DRPC socket).
- See the [CLI contract](../README.md#the-cli-contract-stable-integration-surface)
  to customize.
