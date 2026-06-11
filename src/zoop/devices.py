"""Parse Blip's local ``state.dat`` to recover the signed-in account, its paired
devices, and the contacts (other accounts) the user has interacted with.

``state.dat`` is a Square Wire protobuf. We don't have the ``.proto`` schema, so
we read it with targeted byte patterns. Two entity shapes matter, and they share
a structure:

An *account-like* entity (your own account, or a contact) looks like::

    0a 24 <user_id>            # field 1: user_id (uuid string, len 0x24=36)
    12 <len> {                 # field 2: profile sub-message
        0a <len> <email>       #   field 1: email
        12 <len> <name>        #   field 2: display name
        3a <len> <device> ...  #   field 7: paired device (repeated)
    }

A *device* entry inside ``field 7`` looks like::

    0a 24 <device_id>
    12 <len> {
        0a 24 <device_id>
        10 <type>              #   device kind (2=iPhone,3=iPad,4=Mac,5=PC,...)
        1a <len> <name>        #   present only for your OWN devices
    }

A Blip "peer id" (what ``Blip --peer`` expects) is ``<user_id>:<device_id>``.
Contacts only appear here once you've had a transfer with them; brand-new people
are resolved server-side by Blip and are not available locally.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_UUID = rb"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# Entity header: user_id followed by a profile sub-message (field 2).
_PERSON_RE = re.compile(rb"\x0a\x24(" + _UUID + rb")\x12")

# Device entry: outer id, nested sub-message with inner id, a type byte, and an
# optional name (only your own devices carry a name).
_DEVICE_RE = re.compile(
    rb"\x0a\x24(" + _UUID + rb")"   # outer device_id
    rb"\x12.\x0a\x24" + _UUID +     # field 2 -> inner device_id
    rb"\x10(.)"                     # device type byte
    rb"(?:\x1a(.))?",               # optional name-length byte
    re.S,
)

# Best-effort map of the device "type" enum to a human label, used for contact
# devices which don't carry a name locally.
DEVICE_KINDS = {1: "Android", 2: "iPhone", 3: "iPad", 4: "Mac", 5: "Windows PC", 6: "Linux"}


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = val = 0
    while True:
        b = buf[pos]
        val |= (b & 0x7F) << shift
        pos += 1
        if not b & 0x80:
            return val, pos
        shift += 7


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    user_id: str
    kind: int | None = None

    @property
    def peer(self) -> str:
        return f"{self.user_id}:{self.id}"


@dataclass
class Person:
    user_id: str
    email: str | None
    name: str | None
    is_self: bool
    devices: list[Device] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.name or self.email or self.user_id


@dataclass
class Target:
    """A resolvable send destination (one device of one person)."""
    label: str
    peer: str
    is_self: bool
    owner: str | None
    match_names: list[str]


@dataclass
class Roster:
    people: list[Person]

    @property
    def self_person(self) -> Person | None:
        return next((p for p in self.people if p.is_self), None)

    @property
    def contacts(self) -> list[Person]:
        return [p for p in self.people if not p.is_self]

    def targets(self) -> list[Target]:
        out: list[Target] = []
        seen: set[str] = set()
        for p in self.people:
            multi = len(p.devices) > 1
            for d in p.devices:
                if d.peer in seen:
                    continue
                seen.add(d.peer)
                if p.is_self:
                    label = d.name
                    names = [d.name]
                else:
                    base = p.label
                    label = base if not multi else f"{base} ({d.name})"
                    names = [base, p.email, f"{base} {d.name}", label]
                out.append(Target(
                    label=label, peer=d.peer, is_self=p.is_self, owner=p.email,
                    match_names=[n for n in names if n],
                ))
        return out

    def resolve(self, target: str) -> Target:
        # A full peer id passes straight through.
        if target.count(":") == 1:
            uid, did = target.split(":")
            if uid and did:
                return Target(label=target, peer=target, is_self=False, owner=None,
                              match_names=[target])
        targets = self.targets()
        t = target.lower()
        exact = [x for x in targets if any(n.lower() == t for n in x.match_names)]
        matches = exact or [x for x in targets if any(t in n.lower() for n in x.match_names)]
        if not matches:
            known = ", ".join(x.label for x in targets) or "(none)"
            raise LookupError(
                f"No recipient matching '{target}'. Known: {known}.\n"
                "If this is someone you haven't transferred with before, they "
                "aren't stored locally yet: open the Blip app, search for them, "
                "and send them anything once. They'll then appear here and be "
                "addressable by name."
            )
        # collapse duplicates that point at the same peer
        uniq = {x.peer: x for x in matches}
        if len(uniq) > 1:
            known = ", ".join(x.label for x in uniq.values())
            raise LookupError(f"'{target}' is ambiguous between: {known}")
        return next(iter(uniq.values()))


def _parse_devices(sub: bytes, user_id: str) -> list[Device]:
    devices: list[Device] = []
    seen: set[str] = set()
    for mm in _DEVICE_RE.finditer(sub):
        dev_id = mm.group(1).decode()
        if dev_id in seen:
            continue
        seen.add(dev_id)
        kind = mm.group(2)[0] if mm.group(2) else None
        name = None
        if mm.group(3) is not None:
            nlen = mm.group(3)[0]
            start = mm.end()
            name = sub[start:start + nlen].decode("utf-8", "replace")
        if not name:
            name = DEVICE_KINDS.get(kind, "device")
        devices.append(Device(id=dev_id, name=name, user_id=user_id, kind=kind))
    return devices


def parse_state(data: bytes) -> Roster:
    by_uid: dict[str, Person] = {}
    for m in _PERSON_RE.finditer(data):
        uid = m.group(1).decode()
        try:
            length, p = _read_varint(data, m.end())
        except IndexError:
            continue
        sub = data[p:p + length]

        email = name = None
        if sub[:1] == b"\x0a":
            try:
                elen, q = _read_varint(sub, 1)
                cand = sub[q:q + elen].decode("utf-8", "replace")
                if "@" in cand:
                    email = cand
                r = q + elen
                if sub[r:r + 1] == b"\x12":
                    nlen, s = _read_varint(sub, r + 1)
                    name = sub[s:s + nlen].decode("utf-8", "replace")
            except (IndexError, UnicodeDecodeError):
                pass

        devices = _parse_devices(sub, uid)
        if email is None and not devices:
            continue  # not an account-like entity (e.g. a transfer peer-ref)

        existing = by_uid.get(uid)
        if existing is None or (not existing.devices and devices):
            by_uid[uid] = Person(user_id=uid, email=email, name=name,
                                  is_self=False, devices=devices)

    people = list(by_uid.values())
    # Heuristic: only your OWN devices carry names locally. The account whose
    # devices have real (non-kind) names is "self".
    kind_labels = set(DEVICE_KINDS.values()) | {"device"}
    for person in people:
        if any(d.name not in kind_labels for d in person.devices):
            person.is_self = True
    return Roster(people=people)


def load_roster(state_path) -> Roster:
    with open(state_path, "rb") as fh:
        return parse_state(fh.read())
