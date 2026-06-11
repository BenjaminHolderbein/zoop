"""Native macOS send path.

The Mac Blip app has no ``--peer``/``--file`` CLI (that's Windows-only). Instead
its background core exposes a local RPC over a unix socket in Blip's App Group
container. The protocol is **DRPC** (storj.io/drpc) — a tiny framed RPC, *not*
gRPC/HTTP2 — carrying protobuf ``event`` messages on a single method,
``/rpc.Service/Dispatch``.

A send is three dispatched events::

    TransferCreateRequested { transfer_id, peer_id }
    TransferAddContentRequested { transfer_id, locations[] }
    TransferInviteRequested { transfer_id, peer_id }

Each ``DispatchRequest.event`` is a ``google.protobuf.Any`` wrapping the event.
We hand-roll the (small, fixed) protobuf and DRPC framing so this stays pure
stdlib — no protobuf/grpc/drpc dependencies. Wire format reverse-engineered from
the shipping app (see Heap notes / memory ``zoop-mac-internals``).
"""

from __future__ import annotations

import os
import socket
import uuid

_RPC_PATH = b"/rpc.Service/Dispatch"

# DRPC frame kinds we emit/recognize (low bits of the control byte; bit 0x08 = Done).
_K_INVOKE = 0x03
_K_MESSAGE = 0x05
_K_MESSAGE_DONE = 0x0D  # _K_MESSAGE | 0x08
_K_INVOKE_DONE = 0x0B   # _K_INVOKE | 0x08
_K_ERROR = 0x07         # error frames carry a payload


# ---- protobuf (varint + length-delimited only; that's all these messages use) ----

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


def _ld(field: int, data: bytes) -> bytes:
    """Encode a length-delimited (wire type 2) field: string, bytes, or message."""
    return _varint((field << 3) | 2) + _varint(len(data)) + data


def _s(field: int, text: str) -> bytes:
    return _ld(field, text.encode("utf-8"))


def _peer(user_id: str, device_id: str) -> bytes:
    return _s(1, user_id) + _s(2, device_id)


def _any(type_name: str, payload: bytes) -> bytes:
    # google.protobuf.Any { type_url = 1, value = 2 }
    return _s(1, "type.googleapis.com/event." + type_name) + _ld(2, payload)


def _dispatch_request(event_any: bytes) -> bytes:
    # rpc.DispatchRequest { event = 1 (bytes) }
    return _ld(1, event_any)


# ---- DRPC framing ----

def _frame(control: int, stream: int, message: int, data: bytes = b"") -> bytes:
    return bytes([control]) + _varint(stream) + _varint(message) + _varint(len(data)) + data


def _invoke_frames(stream: int, payload: bytes) -> bytes:
    """The 4 frames a unary DRPC client sends for one call."""
    return (
        _frame(_K_INVOKE, stream, 1, _RPC_PATH)
        + _frame(_K_MESSAGE, stream, 2, payload)
        + _frame(_K_MESSAGE_DONE, stream, 3)
        + _frame(_K_INVOKE_DONE, stream, 4)
    )


def _read_varint(buf: bytes, pos: int):
    shift = val = 0
    while True:
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not b & 0x80:
            return val, pos
        shift += 7


def _scan_for_error(buf: bytes) -> None:
    """Walk DRPC frames in ``buf`` and raise if the core returned an Error frame."""
    pos = 0
    while pos < len(buf):
        try:
            control = buf[pos]
            p = pos + 1
            _stream, p = _read_varint(buf, p)
            _msg, p = _read_varint(buf, p)
            ln, p = _read_varint(buf, p)
        except IndexError:
            break
        if p + ln > len(buf):
            break
        payload = buf[p:p + ln]
        if (control & 0x07) == _K_ERROR and payload:
            raise RuntimeError("Blip core error: " + payload.decode("utf-8", "replace"))
        pos = p + ln


def send(sock_path: str, user_id: str, device_id: str, files: list[str], *,
         error_wait: float = 0.5) -> str:
    """Create a transfer of ``files`` to ``user_id:device_id`` and send the invite.

    The core processes each event the moment it arrives, so we pipeline all three
    dispatches on one connection (Create, then AddContent, then Invite). The
    core's per-call success responses flush lazily and aren't needed for
    delivery; we do a short best-effort read only to surface an early Error
    frame, then return. Returns the transfer id.
    """
    tid = str(uuid.uuid4())
    peer = _peer(user_id, device_id)
    events = [
        ("TransferCreateRequested", _s(1, tid) + _ld(2, peer)),
        ("TransferAddContentRequested",
         _s(1, tid) + b"".join(_s(2, os.path.abspath(f)) for f in files)),
        ("TransferInviteRequested", _s(1, tid) + _ld(2, peer)),
    ]

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(10)
    s.connect(sock_path)
    try:
        out = b"".join(
            _invoke_frames(i, _dispatch_request(_any(name, body)))
            for i, (name, body) in enumerate(events, start=1)
        )
        s.sendall(out)
        # Opportunistic error check; success responses may never arrive (lazy
        # server flush) and that's fine — the events are already being processed.
        s.settimeout(error_wait)
        resp = b""
        try:
            while len(resp) < 4096:
                chunk = s.recv(4096)
                if not chunk:
                    break
                resp += chunk
        except socket.timeout:
            pass
        _scan_for_error(resp)
    finally:
        s.close()
    return tid
