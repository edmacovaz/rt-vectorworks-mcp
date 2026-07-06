#!/usr/bin/env python3
"""Host-side smoke check for a live VW MCP session (stdlib only, no deps).

Run on the same Mac as Vectorworks, while a VW MCP session (the modal listener
started from the installed menu Command) is open, to confirm the loopback round
trip and inspect the capability flags:

    python3 scripts/vw_ping.py

It sends one read-only ``ping`` over TCP loopback and prints whether the session
is CAD-safe (``cad_api_safe`` / ``transport_only`` / ``dispatch_mode``). It uses
only the Python that ships with macOS — so it works from a downloaded ZIP with
nothing installed. This is the quick manual check in the LAB-9 handoff; the full
MCP round trip is driven by the host server (``vw_mcp.server``) via the client.
"""

import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 9877
TIMEOUT_S = 5


def main() -> int:
    request = json.dumps({"action": "ping"}) + "\n"
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT_S) as sock:
            sock.sendall(request.encode("utf-8"))
            buf = bytearray()
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf.extend(chunk)
    except OSError as exc:
        print(
            "FAIL: could not reach a VW MCP session on {}:{} — {}".format(
                HOST, PORT, exc
            )
        )
        print("Is a session open inside VW, on this machine?")
        return 1

    line = bytes(buf).partition(b"\n")[0].strip()
    if not line:
        print("FAIL: session closed without responding.")
        return 1
    try:
        resp = json.loads(line.decode("utf-8"))
    except ValueError:
        print("FAIL: non-JSON response: {!r}".format(line))
        return 1

    if not resp.get("ok"):
        print("FAIL: ping returned an error: {}".format(resp.get("error")))
        return 1

    if resp.get("cad_api_safe") and not resp.get("transport_only"):
        print(
            "PASS: CAD-safe session (dispatch_mode={!r}, bridge_kind={!r}). "
            "Open document filename = {!r}".format(
                resp.get("dispatch_mode"), resp.get("bridge_kind"), resp.get("filename")
            )
        )
        return 0

    print(
        "TRANSPORT-ONLY: reachable but not CAD-safe "
        "(dispatch_mode={!r}, error={!r}). The socket answers but vs.* is unsafe.".format(
            resp.get("dispatch_mode"), resp.get("error")
        )
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
