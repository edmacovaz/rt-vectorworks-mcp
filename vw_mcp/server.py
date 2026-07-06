"""The host-side MCP server (FastMCP), exposing a read-only Vectorworks tool.

This runs on the host, not inside Vectorworks: the tool forwards a request to
the in-VW companion over a *companion transport* and shapes the reply. That
transport is a seam — in production it is a TCP client to the loopback listener
(:func:`tcp_companion`), but the server only depends on its shape, so it can be
driven with Vectorworks closed by an in-process stub (:func:`in_process_companion`).

The one tool is ``vw_ping``: it returns a real ``vs.*`` value (the open document's
filename) **plus** capability flags (``cad_api_safe`` / ``transport_only`` /
``dispatch_mode`` / ``bridge_kind``). The flags are earned, not declared — the
in-VW listener only reports ``cad_api_safe=true`` when the real read just
succeeded — so a healthy CAD-safe session is distinguishable from a merely
socket-reachable ``transport_only`` one (see :mod:`vw_mcp.dispatch`).
"""

from __future__ import annotations

import json
import os
import socket
from typing import Any, Callable

from fastmcp import FastMCP

from vw_mcp.dispatch import handle_request
from vw_mcp.framing import LineFramer, encode_message
from vw_mcp.vs_adapter import StubVsAdapter, VsPort

# Send one request dict to the in-VW companion, get its response dict back.
Companion = Callable[[dict[str, Any]], dict[str, Any]]

# Loopback transport defaults, proven end-to-end on macOS/VW 2026 in LAB-9.
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9877
DEFAULT_TIMEOUT = 5.0


def in_process_companion(vs: VsPort) -> Companion:
    """A companion that runs the dispatch logic in-process against ``vs``.

    Stands in for the real TCP-to-Vectorworks transport so the server can be
    driven with Vectorworks closed (tests, local smoke runs). ``dispatch_mode``
    is ``"stub"`` — this path is never a live CAD session.
    """

    def send(request: dict[str, Any]) -> dict[str, Any]:
        return handle_request(request, vs, dispatch_mode="stub")

    return send


def tcp_companion(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> Companion:
    """The real companion: a TCP client to the in-VW loopback listener.

    Opens a short-lived connection per request, sends one newline-JSON line, and
    reads one line back (same wire format the listener speaks, via
    :mod:`vw_mcp.framing`). Kept deliberately simple — a request/response round
    trip, no persistent connection state on the host side.
    """

    def send(request: dict[str, Any]) -> dict[str, Any]:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(encode_message(request))
            framer = LineFramer()
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    raise RuntimeError(
                        "companion closed the connection before replying "
                        "(is a VW MCP session open on {}:{}?)".format(host, port)
                    )
                lines = framer.feed(chunk)
                if lines:
                    try:
                        reply = json.loads(lines[0].decode("utf-8"))
                    except ValueError as exc:
                        raise RuntimeError(
                            "companion sent malformed JSON: {}".format(exc)
                        )
                    if not isinstance(reply, dict):
                        raise RuntimeError(
                            "companion sent a non-object reply: {!r}".format(reply)
                        )
                    return reply

    return send


def build_server(companion: Companion) -> FastMCP:
    """Build the MCP server. ``companion`` is the seam to the in-VW listener."""
    mcp: FastMCP = FastMCP("vw-mcp-poc")

    @mcp.tool
    def vw_ping() -> dict[str, Any]:
        """Reach the live Vectorworks document and report health.

        Returns the open document's ``filename`` (a real ``vs.*`` read) together
        with capability flags: ``cad_api_safe`` (the read actually worked),
        ``transport_only`` (socket answered but CAD is unsafe), ``dispatch_mode``,
        and ``bridge_kind``. A healthy session has ``cad_api_safe=true`` and
        ``transport_only=false``; ``filename`` is null when CAD is unsafe.
        """
        try:
            resp = companion({"action": "ping"})
        except OSError as exc:
            # No listener reachable — the common "VW closed / no session open"
            # case. Surface it as a clear, actionable error rather than leaking a
            # raw socket exception to the client.
            raise RuntimeError(
                "could not reach a VW MCP session — open one from the "
                "VW MCP Session menu command in Vectorworks ({})".format(exc)
            )
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "companion ping failed"))
        return {
            "filename": resp.get("filename"),
            "cad_api_safe": bool(resp.get("cad_api_safe", False)),
            "transport_only": bool(resp.get("transport_only", True)),
            "dispatch_mode": resp.get("dispatch_mode", "unknown"),
            "bridge_kind": resp.get("bridge_kind", "unknown"),
        }

    return mcp


def build_default_server() -> FastMCP:
    """Server wired to an in-process stub companion — no Vectorworks, no socket.

    Enough to introspect or smoke-run the server locally (and to drive the tool
    in the no-Vectorworks test net).
    """
    return build_server(in_process_companion(StubVsAdapter()))


def build_tcp_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    timeout: float = DEFAULT_TIMEOUT,
) -> FastMCP:
    """The production server: real TCP transport to a live in-VW listener."""
    return build_server(tcp_companion(host, port, timeout))


def _env_number(name: str, default: "int | float", cast: Callable[[str], Any]) -> Any:
    """Read a numeric env override, falling back to ``default`` if unset/invalid.

    The launch config wires these in as strings; a blank or mistyped value must
    not crash the server at startup with an opaque traceback.
    """
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return cast(raw)
    except ValueError:
        return default


def _server_from_env() -> FastMCP:
    """Build the production TCP server, honouring ``VW_MCP_*`` env overrides."""
    host = os.environ.get("VW_MCP_HOST", DEFAULT_HOST)
    port = _env_number("VW_MCP_PORT", DEFAULT_PORT, int)
    timeout = _env_number("VW_MCP_TIMEOUT", DEFAULT_TIMEOUT, float)
    return build_tcp_server(host, port, timeout)


if __name__ == "__main__":
    # The installed MCP client launches this: the real transport to live VW.
    _server_from_env().run()
