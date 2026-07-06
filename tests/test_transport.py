"""The real TCP transport, end-to-end with Vectorworks closed.

Drives the production host client (:func:`~vw_mcp.server.tcp_companion`) against
the production in-VW socket server (:class:`~vw_mcp.listener.SocketPump`) over a
real loopback connection — the same wire the live round trip uses — with the
``vs`` seam stubbed. Only the modal *dialog* needs Vectorworks; the socket path
does not, so it is checkable here. The pump is driven from a background thread
(in VW it is driven by the dialog timer instead).
"""

import threading
import time

from vw_mcp.listener import SocketPump
from vw_mcp.server import tcp_companion
from vw_mcp.vs_adapter import StubVsAdapter


def _pump_until(pump, stop):
    while not stop.is_set():
        pump.pump()
        time.sleep(0.001)


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
