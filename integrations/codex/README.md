# Codex integration

Send files via Blip from [OpenAI Codex](https://developers.openai.com/codex)
by natural language ("blip this to my mac").

Codex consumes the same **Agent Skill** (`SKILL.md`) format as Claude, so this is
just the engine + a skill file.

## Install

1. **Engine** (one-time, on PATH):

   ```
   pipx install git+https://github.com/BenjaminHolderbein/zoop
   zoop doctor      # verify it finds Blip
   ```

2. **Skill** — copy this skill into your Codex skills directory:

   ```
   # global (available in every Codex session):
   cp -r skills/zoop ~/.codex/skills/

   # or, per-repo: Codex auto-discovers skills under .agents/skills/
   cp -r skills/zoop /path/to/your/repo/.agents/skills/
   ```

   (On Windows, copy the `skills/zoop` folder into
   `%USERPROFILE%\.codex\skills\`.)

## Use

In Codex: *"blip this file to my iPhone"*, *"send report.pdf to my mac with
blip"*. Codex activates the skill and runs `zoop` for you. You can also use
`/skills` to pick it explicitly.

## Notes

- macOS is supported with no extra setup — the engine talks to Blip's local DRPC
  socket internally.
- See the [CLI contract](../README.md#the-cli-contract-stable-integration-surface)
  if you want to customize behavior.
