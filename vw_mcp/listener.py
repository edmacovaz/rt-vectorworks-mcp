"""In-Vectorworks listener runtime: a modal agent-session dialog + socket pump.

This is the VW-only half of the round trip — the production replacement for the
LAB-9 spike's ``vw_modal_listener.py``. It adds the two things that only exist
inside Vectorworks (a non-blocking loopback socket server, pumped from a modal
dialog's timer so VW's UI never freezes) on top of the *tested* pure core it
imports: :mod:`vw_mcp.framing`, :mod:`vw_mcp.dispatch`, and the ``vs`` seam in
:mod:`vw_mcp.vs_adapter`. There is no second copy of the request/framing logic —
the same code the no-Vectorworks net checks is what runs live.

Split for testability: :class:`SocketPump` is plain stdlib (it drives reads
through the injected ``vs`` seam, never ``vs`` directly) and is exercised
off-Vectorworks in the test net; only :func:`run` touches Vectorworks — and only
for the *dialog UI* calls, which have no read semantics. All CAD reads still go
through the adapter, so the seam's testability guarantee holds.

Runs inside VW 2026's embedded Python 3.9 — keep it 3.9-compatible and never
import ``fastmcp`` here (that is host-only).
"""

from __future__ import annotations

import select
import socket
from typing import Any, Dict, List, Optional

from vw_mcp.dispatch import handle_line
from vw_mcp.framing import LineFramer, encode_message
from vw_mcp.vs_adapter import VsPort

# ``vs`` exists only inside Vectorworks. SocketPump never uses it (it goes
# through the injected VsPort adapter); it is imported here solely for the
# dialog UI calls in run(), which are the VW-UI boundary, not companion logic.
try:
    import vs  # provided by Vectorworks' embedded Python; absent everywhere else
except ImportError:  # pragma: no cover - lets the module import for tests/linting
    vs = None

HOST = "127.0.0.1"
PORT = 9877

# The lifecycle mode this listener runs in: a modal, turn-taking agent session.
# Reported in the ``ping`` tool's capability flags (see vw_mcp.dispatch).
DISPATCH_MODE = "dialog"

# Milliseconds between dialog timer ticks; each tick pumps the socket. Small
# enough to feel instant, large enough not to burn CPU (proven in the spike).
TIMER_MS = 50

# SetupDialogC — the event VW fires once when a layout dialog first opens; we
# register the timer there. 12255 is the documented constant.
_SETUP_EVENT = getattr(vs, "SetupDialogC", 12255) if vs is not None else 12255

_STATUS_ITEM = 4
_HINT_ITEM = 5

# Bound the accepted-connection table so a stalled or half-open peer (a port
# scanner, a client killed mid-request) can't leak file descriptors over a long
# session. Cooperating clients open, get one reply, and close, so this only ever
# trips on misbehaving peers.
_MAX_CONNS = 64

# Reply on a briefly-blocking socket so a large payload isn't dropped by a full
# non-blocking send buffer; the timeout bounds a pathological non-reading client.
# (For the POC's tiny ping the buffer never fills; a full non-blocking write
# buffer is the deeper fix once a tool returns a large reply to a slow reader.)
_SEND_TIMEOUT_S = 5.0


class SocketPump:
    """Non-blocking newline-JSON server for the in-VW listener.

    Pure stdlib: it accepts loopback connections, reassembles wire lines with
    :class:`~vw_mcp.framing.LineFramer`, dispatches each through
    :func:`~vw_mcp.dispatch.handle_line` against the injected ``vs`` seam, and
    writes the reply back. ``pump`` never blocks, so it is safe to call from the
    dialog timer on VW's UI thread. Reads flow through ``vs`` (a
    :class:`~vw_mcp.vs_adapter.VsPort`), so this whole class runs — and is
    tested — with Vectorworks closed against a stub.
    """

    def __init__(
        self,
        vs_port: VsPort,
        host: str = HOST,
        port: int = PORT,
        dispatch_mode: str = DISPATCH_MODE,
    ) -> None:
        self._vs = vs_port
        self._host = host
        self._port = port
        self._dispatch_mode = dispatch_mode
        self._server: Optional[socket.socket] = None
        self._conns: Dict[socket.socket, LineFramer] = {}

    def start(self) -> None:
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self._host, self._port))
        srv.listen(8)
        srv.setblocking(False)
        self._server = srv

    @property
    def port(self) -> int:
        """The actually-bound port (useful when constructed with ``port=0``)."""
        if self._server is None:
            return self._port
        return self._server.getsockname()[1]

    def pump(self) -> None:
        """Accept, read, dispatch, reply — all without blocking. One tick."""
        if self._server is None:
            return
        rlist: List[socket.socket] = [self._server] + list(self._conns)
        try:
            readable, _, _ = select.select(rlist, [], [], 0)
        except (OSError, ValueError):
            return
        for sock in readable:
            if sock is self._server:
                self._accept()
            else:
                self._read(sock)

    def _accept(self) -> None:
        try:
            conn, _addr = self._server.accept()
        except (BlockingIOError, OSError):
            return
        conn.setblocking(False)
        # Drop the oldest connection if we're at the cap (dict is insertion-
        # ordered), so a stalled peer that never sends can't pin an FD forever.
        if len(self._conns) >= _MAX_CONNS:
            self._close(next(iter(self._conns)))
        self._conns[conn] = LineFramer()

    def _read(self, conn: socket.socket) -> None:
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
        for line in self._conns[conn].feed(chunk):
            resp = handle_line(line, self._vs, self._dispatch_mode)
            if not self._send(conn, encode_message(resp)):
                return

    def _send(self, conn: socket.socket, payload: bytes) -> bool:
        """Send one reply, tolerating a full send buffer. Returns False on close."""
        try:
            conn.settimeout(_SEND_TIMEOUT_S)  # block (bounded) rather than drop
            conn.sendall(payload)
            return True
        except OSError:
            self._close(conn)
            return False
        finally:
            try:
                conn.settimeout(0.0)  # restore non-blocking for select-driven reads
            except OSError:
                pass

    def _close(self, conn: socket.socket) -> None:
        self._conns.pop(conn, None)
        try:
            conn.close()
        except OSError:
            pass

    def close(self) -> None:
        for conn in list(self._conns):
            self._close(conn)
        if self._server is not None:
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None


def _set_status(dialog_id: Any, item_id: int, text: str) -> None:
    """Best-effort update of a dialog's static text (setter name varies by build)."""
    for setter in ("SetControlText", "SetItemText"):
        fn = getattr(vs, setter, None)
        if fn is not None:
            try:
                fn(dialog_id, item_id, text)
                return
            except Exception:
                pass


def run() -> None:
    """Open the modal agent-session dialog and pump the socket while it is open.

    This is the entry point the on-disk stable loader reads-and-runs from the
    Plug-in Manager Command. It runs the CAD reads through the ``vs`` seam
    (:class:`~vw_mcp.vs_adapter.VectorworksAdapter`) and uses the module-level
    ``vs`` only for the dialog UI. Closing the dialog hands Vectorworks back.
    """
    if vs is None:
        raise RuntimeError(
            "vw_mcp.listener.run() must run inside Vectorworks (no vs module)."
        )

    from vw_mcp.vs_adapter import VectorworksAdapter

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
        vs.AlrtDialog(
            "VW 2026 is missing dialog APIs this listener needs:\n" + ", ".join(missing)
        )
        return

    pump = SocketPump(VectorworksAdapter())
    try:
        pump.start()
    except OSError as exc:
        vs.AlrtDialog("Could not bind {}:{} — {}".format(HOST, PORT, exc))
        return

    dialog_id = vs.CreateLayout("VW MCP Session", False, "Stop", "")
    vs.CreateStaticText(
        dialog_id, _STATUS_ITEM, "Agent session on {}:{}".format(HOST, PORT), 48
    )
    vs.CreateStaticText(
        dialog_id,
        _HINT_ITEM,
        "Agent drives VW while this is open; close to hand it back.",
        56,
    )
    vs.SetFirstLayoutItem(dialog_id, _STATUS_ITEM)
    vs.SetBelowItem(dialog_id, _STATUS_ITEM, _HINT_ITEM, 0, 0)

    timer_registered = [False]

    def handler(item: int, data: Any) -> None:
        if item == _SETUP_EVENT:
            try:
                vs.RegisterDialogForTimerEvents(dialog_id, TIMER_MS)
                timer_registered[0] = True
            except Exception as exc:
                # Without timer ticks the socket only pumps once and calls hang —
                # surface it instead of failing silently.
                _set_status(
                    dialog_id,
                    _STATUS_ITEM,
                    "NO-GO: timer registration failed, socket won't pump: {}".format(
                        exc
                    ),
                )
            pump.pump()
            return
        if item in (1, 2):  # "Stop" (OK) or Cancel — end the session
            return
        # Any other event (chiefly the timer tick) -> pump the socket.
        pump.pump()

    try:
        vs.RunLayoutDialog(dialog_id, handler)
    finally:
        if timer_registered[0]:
            try:
                vs.DeregisterDialogFromTimerEvents(dialog_id)
            except Exception:
                pass
        pump.close()


if __name__ == "__main__":
    run()

# Note: importing this module has NO side effects — it never auto-starts the
# session. The installed stable loader is what runs it: it execs this file in a
# fresh namespace and then calls ``run()`` explicitly (see scripts/install.py).
