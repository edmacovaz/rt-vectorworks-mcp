"""The real TCP transport, end-to-end with Vectorworks closed.

Drives the production host client (:func:`~vw_mcp.server.tcp_companion`) against
the production in-VW socket server (:class:`~vw_mcp.listener.SocketPump`) over a
real loopback connection — the same wire the live round trip uses — with the
``vs`` seam stubbed. Only the modal *dialog* needs Vectorworks; the socket path
does not, so it is checkable here. The pump is driven from a background thread
(in VW it is driven by the dialog timer instead).
"""

import socket
import threading
import time

import pytest

from vw_mcp.listener import SocketPump
from vw_mcp.server import tcp_companion
from vw_mcp.vs_adapter import StubVsAdapter


def _pump_until(pump, stop):
    while not stop.is_set():
        pump.pump()
        time.sleep(0.001)


def _serve_once(reply: bytes) -> int:
    """Spin up a one-shot loopback server that sends ``reply`` and closes."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]

    def handle():
        conn, _ = srv.accept()
        with conn:
            conn.recv(65536)
            if reply:
                conn.sendall(reply)
        srv.close()

    threading.Thread(target=handle, daemon=True).start()
    return port


def test_tcp_companion_round_trips_against_the_socket_pump():
    pump = SocketPump(
        StubVsAdapter("Loop.vwx"), host="127.0.0.1", port=0, dispatch_mode="dialog"
    )
    pump.start()
    stop = threading.Event()
    thread = threading.Thread(target=_pump_until, args=(pump, stop))
    thread.start()
    try:
        send = tcp_companion("127.0.0.1", pump.port, timeout=5.0)
        resp = send({"action": "ping"})
    finally:
        stop.set()
        thread.join()
        pump.close()

    assert resp["ok"] is True
    assert resp["cad_api_safe"] is True
    assert resp["transport_only"] is False
    assert resp["dispatch_mode"] == "dialog"
    assert resp["filename"] == "Loop.vwx"


def test_unreachable_port_raises_oserror():
    # Nothing is listening — the host client surfaces an OSError, which vw_ping
    # turns into a clear "no session reachable" message and the e2e test skips on.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        dead_port = probe.getsockname()[1]  # bound-but-not-listening → refused
    send = tcp_companion("127.0.0.1", dead_port, timeout=2.0)
    with pytest.raises(OSError):
        send({"action": "ping"})


def test_non_object_reply_is_a_runtime_error():
    port = _serve_once(b"[1, 2, 3]\n")  # valid JSON, but not an object
    send = tcp_companion("127.0.0.1", port, timeout=2.0)
    with pytest.raises(RuntimeError):
        send({"action": "ping"})


def test_reply_dropped_before_completion_is_a_runtime_error():
    port = _serve_once(b"")  # accept, then close without replying
    send = tcp_companion("127.0.0.1", port, timeout=2.0)
    with pytest.raises(RuntimeError):
        send({"action": "ping"})
