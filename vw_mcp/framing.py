"""The server ↔ in-Vectorworks wire format: newline-delimited JSON.

One JSON object per line, one request or response per line (the format proven in
the LAB-9 spike). :class:`LineFramer` turns an arbitrarily-chunked byte stream
back into whole lines; :func:`encode_message` produces a line to send. Both are
pure, so the round trip is checkable with Vectorworks closed.
"""

from __future__ import annotations

import json
from typing import Any


class LineFramer:
    """Reassembles a byte stream into complete newline-delimited messages.

    ``feed`` is pure buffering: hand it whatever bytes arrive — a partial line,
    several lines at once, a line split across chunks — and it returns the
    complete lines it can now emit, holding any trailing partial line until the
    rest arrives. Blank lines are dropped.
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> list[bytes]:
        self._buf.extend(chunk)
        lines: list[bytes] = []
        while True:
            newline = self._buf.find(b"\n")
            if newline == -1:
                break
            line = bytes(self._buf[:newline]).strip()
            del self._buf[: newline + 1]
            if line:
                lines.append(line)
        return lines


def encode_message(obj: Any) -> bytes:
    """Serialise one message object to a single wire line (JSON + newline)."""
    return (json.dumps(obj) + "\n").encode("utf-8")
