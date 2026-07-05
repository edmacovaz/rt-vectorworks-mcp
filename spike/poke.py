#!/usr/bin/env python3
"""LAB-9 Probe A — loopback poke client (DISPOSABLE).

Stands in for the MCP server/client (out of scope for this spike, see LAB-6):
connects to the modal listener over loopback, sends one read-only request, and
prints the open document's filename it gets back. Success here means the modal
dialog pumped the socket and answered a real ``vs.*`` call without freezing VW.

Run this on the SAME machine as VW, while ``spike/vw_modal_listener.py`` is
running as a modal dialog:

    python3 spike/poke.py

Stdlib only — no dependencies.
"""

import json
import socket
import sys

HOST = "127.0.0.1"
PORT = 9877
TIMEOUT_S = 5


def main():
    request = json.dumps({"action": "filename"}) + "\n"
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT_S) as sock:
            sock.sendall(request.encode("utf-8"))
            # Read one newline-delimited response line.
            buf = bytearray()
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf.extend(chunk)
    except OSError as exc:
        print("FAIL: could not reach listener on {}:{} — {}".format(HOST, PORT, exc))
        print("Is the modal spike running inside VW, on this machine?")
        return 1

    line = bytes(buf).partition(b"\n")[0].strip()
    if not line:
        print("FAIL: listener closed without responding.")
        return 1

    try:
        resp = json.loads(line.decode("utf-8"))
    except ValueError:
        print("FAIL: non-JSON response: {!r}".format(line))
        return 1

    if resp.get("ok"):
        print("PASS: round trip OK. Open document filename = {!r}".format(resp.get("filename")))
        return 0

    print("FAIL: listener returned an error: {}".format(resp.get("error")))
    return 1


if __name__ == "__main__":
    sys.exit(main())
