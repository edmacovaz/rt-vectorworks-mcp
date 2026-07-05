"""LAB-9 Probe A — modal-dialog socket-pump spike (DISPOSABLE).

Goal: prove, on macOS + Vectorworks 2026, that a modal-dialog "agent session"
can pump a loopback TCP socket *without freezing VW's UI* and answer one
read-only ``vs.*`` call (the open document's filename).

This is a throwaway feasibility probe, not the production listener. It is
deliberately hardcoded and dependency-free (stdlib ``socket``/``select``/``json``
+ the in-VW ``vs`` module) — the MCP protocol layer is out of scope here and
belongs to LAB-6 (which will build on FastMCP). See ``spike/README.md`` for how
to run it.

How to run (Probe A):
  1. In VW 2026: Resource Manager (Cmd+R) -> New Resource -> Script ->
     Python -> paste this whole file -> run.
  2. A modal "VW MCP Spike" dialog opens and stays open. VW should remain
     responsive (pan/zoom the document) while it is open.
  3. From a terminal on the same machine, run ``python3 spike/poke.py``.
     It should print the open document's real filename.
  4. Click "Stop" (or close the dialog) to end the session and hand VW back.

Wire format: newline-delimited JSON over TCP loopback. One request object per
line, one response object per line. The only supported request is
``{"action": "filename"}``.
"""

import json
import select
import socket

try:
    import vs  # Provided by Vectorworks' embedded Python; absent outside VW.
except ImportError:  # pragma: no cover - lets the file be imported for linting.
    vs = None

HOST = "127.0.0.1"
PORT = 9877

# SetupDialogC — the event VW fires once when a layout dialog first opens.
# We register the timer here so the socket starts getting pumped. 12255 is the
# documented constant; getattr keeps the spike honest if the name is exposed.
SETUP_EVENT = getattr(vs, "SetupDialogC", 12255) if vs is not None else 12255

# Milliseconds between timer ticks. Each tick pumps the socket. Small enough to
# feel instant, large enough not to burn CPU.
TIMER_MS = 50

_STATUS_ITEM = 4
_HINT_ITEM = 5


def _handle_request(req):
    """Answer one request dict. Read-only only — refuse anything else."""
    action = req.get("action")
    if action == "filename":
        # The one read-only CAD value this probe proves it can return.
        return {"ok": True, "action": "filename", "filename": vs.GetFName() or "Untitled"}
    return {"ok": False, "error": "unsupported action: {!r}".format(action)}


class _SpikeServer:
    """Minimal non-blocking, newline-delimited JSON server.

    Deliberately simpler than the prior-art length-prefixed framing: a probe
    only has to answer one call cleanly. ``pump()`` never blocks, so it is safe
    to call from the dialog's timer handler on VW's UI thread.
    """

    def __init__(self):
        self._server = None
        self._conns = {}  # socket -> bytearray read buffer

    def start(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(8)
        srv.setblocking(False)
        self._server = srv

    def pump(self):
        """Accept, read, dispatch, reply — all without blocking. One tick."""
        if self._server is None:
            return
        rlist = [self._server] + list(self._conns)
        try:
            readable, _, _ = select.select(rlist, [], [], 0)
        except (OSError, ValueError):
            return
        for sock in readable:
            if sock is self._server:
                self._accept()
            else:
                self._read(sock)

    def _accept(self):
        try:
            conn, _addr = self._server.accept()
        except (BlockingIOError, OSError):
            return
        conn.setblocking(False)
        self._conns[conn] = bytearray()

    def _read(self, conn):
        try:
            chunk = conn.recv(65536)
        except (BlockingIOError, InterruptedError):
            return
        except OSError:
            self._close(conn)
            return
        if not chunk:  # peer closed
            self._close(conn)
            return
        buf = self._conns[conn]
        buf.extend(chunk)
        while b"\n" in buf:
            line, _, rest = bytes(buf).partition(b"\n")
            del buf[:]
            buf.extend(rest)
            self._dispatch_line(conn, line)

    def _dispatch_line(self, conn, line):
        line = line.strip()
        if not line:
            return
        try:
            req = json.loads(line.decode("utf-8"))
            resp = _handle_request(req)
        except Exception as exc:  # bad JSON or handler error -> report, don't crash
            resp = {"ok": False, "error": "bad request: {}".format(exc)}
        payload = (json.dumps(resp) + "\n").encode("utf-8")
        try:
            conn.sendall(payload)
        except OSError:
            self._close(conn)

    def _close(self, conn):
        self._conns.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass

    def close(self):
        for conn in list(self._conns):
            self._close(conn)
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None


def run():
    if vs is None:
        raise RuntimeError("This spike must run inside Vectorworks (vs module unavailable).")

    required = (
        "CreateLayout",
        "CreateStaticText",
        "SetFirstLayoutItem",
        "SetBelowItem",
        "RunLayoutDialog",
        "RegisterDialogForTimerEvents",
        "DeregisterDialogFromTimerEvents",
    )
    missing = [name for name in required if not hasattr(vs, name)]
    if missing:
        vs.AlrtDialog("VW 2026 is missing dialog APIs this probe needs:\n" + ", ".join(missing))
        return

    server = _SpikeServer()
    try:
        server.start()
    except OSError as exc:
        vs.AlrtDialog("Could not bind {}:{} — {}".format(HOST, PORT, exc))
        return

    dialog_id = vs.CreateLayout("VW MCP Spike", False, "Stop", "")
    vs.CreateStaticText(dialog_id, _STATUS_ITEM, "Listening on {}:{}".format(HOST, PORT), 48)
    vs.CreateStaticText(
        dialog_id, _HINT_ITEM, "Keep open while poking; VW should stay responsive.", 56
    )
    vs.SetFirstLayoutItem(dialog_id, _STATUS_ITEM)
    vs.SetBelowItem(dialog_id, _STATUS_ITEM, _HINT_ITEM, 0, 0)

    timer_registered = [False]

    def handler(item, data):
        if item == SETUP_EVENT:
            try:
                vs.RegisterDialogForTimerEvents(dialog_id, TIMER_MS)
                timer_registered[0] = True
            except Exception:
                pass
            server.pump()
            return
        if item in (1, 2):  # "Stop" (OK) or Cancel — end the session
            return
        # Any other event (chiefly the timer tick) -> pump the socket.
        server.pump()

    try:
        vs.RunLayoutDialog(dialog_id, handler)
    finally:
        if timer_registered[0]:
            try:
                vs.DeregisterDialogFromTimerEvents(dialog_id)
            except Exception:
                pass
        server.close()


if __name__ == "__main__":
    run()
else:
    # VW runs a pasted script at module scope, not via __main__.
    run()
