"""Command-line interface for sending files through the genuine Blip app.

Subcommands:
  list     show the signed-in account, its devices, and known contacts (+ peer ids)
  send     send file(s) to a device/contact by name (or by full user_id:device_id)
  doctor   print diagnostics (detected OS, state.dat path, Blip launcher)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import platforms
from .devices import Roster, Target, load_roster


def _load() -> Roster:
    return load_roster(platforms.find_state_dat())


def _resolve(roster: Roster, target: str) -> Target:
    try:
        return roster.resolve(target)
    except LookupError as e:
        raise SystemExit(str(e))


def cmd_list(args: argparse.Namespace) -> int:
    roster = _load()
    if args.json:
        print(json.dumps({
            "self": _person_json(roster.self_person) if roster.self_person else None,
            "contacts": [_person_json(p) for p in roster.contacts],
        }, indent=2))
        return 0

    me = roster.self_person
    if me:
        print(f"you: {me.label} ({me.user_id})")
        for d in me.devices:
            print(f"  {d.name:<18} {d.peer}")
    contacts = roster.contacts
    if contacts:
        print("contacts:")
        for p in contacts:
            for d in p.devices:
                label = p.label if len(p.devices) == 1 else f"{p.label} ({d.name})"
                print(f"  {label:<28} {d.peer}")
    if not me and not contacts:
        print("(no account or contacts found in state.dat)")
    return 0


def _person_json(p) -> dict:
    return {
        "user_id": p.user_id,
        "email": p.email,
        "name": p.name,
        "is_self": p.is_self,
        "devices": [{"id": d.id, "name": d.name, "kind": d.kind, "peer": d.peer}
                    for d in p.devices],
    }


def cmd_send(args: argparse.Namespace) -> int:
    roster = _load()
    target = _resolve(roster, args.to)

    files = []
    for f in args.files:
        p = Path(f).expanduser()
        if not p.exists():
            raise SystemExit(f"File not found: {f}")
        files.append(str(p.resolve()))

    argv = platforms.build_send_argv(target.peer, files)

    if args.dry_run:
        print(" ".join(argv))
        return 0

    print(f"Sending to {target.label} ({target.peer}):")
    for f in files:
        print(f"  {f}")
    proc = subprocess.run(argv)
    if proc.returncode != 0:
        print(f"Blip launcher exited with code {proc.returncode}", file=sys.stderr)
        return proc.returncode
    print("Dispatched to Blip. Check the Blip window / recipient device.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"platform: {sys.platform}")
    print("state.dat candidates:")
    for c in platforms.state_dat_candidates():
        print(f"  [{'x' if c.is_file() else ' '}] {c}")
    try:
        sp = platforms.find_state_dat()
        print(f"using state.dat: {sp}")
        roster = load_roster(sp)
        me = roster.self_person
        if me:
            print(f"account: {me.label} ({me.user_id})")
            print(f"devices: {', '.join(d.name for d in me.devices) or '(none)'}")
        print(f"contacts: {', '.join(p.label for p in roster.contacts) or '(none)'}")
    except Exception as e:  # noqa: BLE001 - diagnostics
        print(f"state.dat: ERROR: {e}")
    print(f"launcher: {' '.join(platforms.launcher_prefix())}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="blip-send", description="Send files via the Blip app.")
    sub = p.add_subparsers(dest="command", required=True)

    pl = sub.add_parser("list", help="list account, devices, and contacts")
    pl.add_argument("--json", action="store_true", help="output JSON")
    pl.set_defaults(func=cmd_list)

    ps = sub.add_parser("send", help="send file(s) to a device or contact")
    ps.add_argument("--to", required=True,
                    help="device/contact name (e.g. 'MacBook Pro', 'Ben') or user_id:device_id")
    ps.add_argument("files", nargs="+", help="one or more file paths")
    ps.add_argument("--dry-run", action="store_true", help="print the Blip command instead of running it")
    ps.set_defaults(func=cmd_send)

    pd = sub.add_parser("doctor", help="print diagnostics")
    pd.set_defaults(func=cmd_doctor)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
