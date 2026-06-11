"""Parser tests using a synthetic state.dat blob.

The fixture is built from the documented byte patterns with fake UUIDs and
names, so no real account data is committed. It contains one self-account (whose
devices carry real names) and one contact (whose device carries only a type, no
name -- the way contacts actually appear in state.dat). Devices are nested inside
each account's profile sub-message, matching the real state.dat layout.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from zoop.devices import parse_state  # noqa: E402

USER_ID = "11111111-1111-4111-8111-111111111111"
DEV_A = "22222222-2222-4222-8222-222222222222"
DEV_B = "33333333-3333-4333-8333-333333333333"

CONTACT_ID = "44444444-4444-4444-8444-444444444444"
CONTACT_DEV = "55555555-5555-4555-8555-555555555555"


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _ld(tag: int, payload: bytes) -> bytes:
    """Length-delimited protobuf field: tag byte + varint length + payload."""
    return bytes([tag]) + _varint(len(payload)) + payload


def _field1_uuid(uuid: str) -> bytes:
    b = uuid.encode()
    assert len(b) == 36
    return b"\x0a\x24" + b


def _device_block(dev_id: str, name: str | None, kind: int = 4) -> bytes:
    nested = _field1_uuid(dev_id) + b"\x10" + bytes([kind])
    if name is not None:
        nested += _ld(0x1a, name.encode())
    # field 7 (0x3a) wrapper holding outer id + nested sub-message
    device = _field1_uuid(dev_id) + _ld(0x12, nested)
    return _ld(0x3a, device)


def _account_block(user_id: str, email: str, name: str, devices: bytes) -> bytes:
    inner = _ld(0x0a, email.encode()) + _ld(0x12, name.encode()) + devices
    return _field1_uuid(user_id) + _ld(0x12, inner)


def build_fixture() -> bytes:
    return b"".join([
        b"\x08\x02\x18\x01",  # arbitrary leading fields
        # self account: devices carry real names
        _account_block(
            USER_ID, "a@example.com", "Me",
            _device_block(DEV_A, "MacBook Pro", kind=4)
            + _device_block(DEV_B, "iPhone", kind=2),
        ),
        # contact: device carries only a type byte (no name)
        _account_block(
            CONTACT_ID, "ben@example.com", "Ben Test Account",
            _device_block(CONTACT_DEV, None, kind=3),  # iPad
        ),
    ])


def test_parse_self_and_devices():
    roster = parse_state(build_fixture())
    me = roster.self_person
    assert me is not None
    assert me.user_id == USER_ID
    names = {d.name: d for d in me.devices}
    assert set(names) == {"MacBook Pro", "iPhone"}
    assert names["MacBook Pro"].id == DEV_A
    assert names["MacBook Pro"].peer == f"{USER_ID}:{DEV_A}"
    assert names["iPhone"].peer == f"{USER_ID}:{DEV_B}"


def test_account_block_not_parsed_as_device():
    roster = parse_state(build_fixture())
    me = roster.self_person
    assert all(d.id != USER_ID for d in me.devices)


def test_contact_parsed():
    roster = parse_state(build_fixture())
    contacts = roster.contacts
    assert len(contacts) == 1
    c = contacts[0]
    assert c.user_id == CONTACT_ID
    assert c.email == "ben@example.com"
    assert c.label == "Ben Test Account"
    assert not c.is_self
    assert len(c.devices) == 1
    # contact device has no local name, so it falls back to the type label
    assert c.devices[0].name == "iPad"
    assert c.devices[0].peer == f"{CONTACT_ID}:{CONTACT_DEV}"


def test_resolve_by_name_and_peer():
    roster = parse_state(build_fixture())
    # device name
    assert roster.resolve("mac").peer == f"{USER_ID}:{DEV_A}"
    # contact name (substring, case-insensitive)
    assert roster.resolve("ben test").peer == f"{CONTACT_ID}:{CONTACT_DEV}"
    # contact email
    assert roster.resolve("ben@example.com").peer == f"{CONTACT_ID}:{CONTACT_DEV}"
    # full peer id passthrough
    peer = f"{CONTACT_ID}:{CONTACT_DEV}"
    assert roster.resolve(peer).peer == peer


if __name__ == "__main__":
    test_parse_self_and_devices()
    test_account_block_not_parsed_as_device()
    test_contact_parsed()
    test_resolve_by_name_and_peer()
    print("ok")
