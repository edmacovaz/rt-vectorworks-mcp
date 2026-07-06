"""The host-side MCP server (FastMCP), exposing read-only Vectorworks tools.

This runs on the host, not inside Vectorworks: each tool forwards a request to
the in-VW companion over a *companion transport* and shapes the reply. That
transport is the second seam — in production it's a TCP client to the loopback
listener (LAB-6), but the server only depends on its shape, so it can be driven
with Vectorworks closed by an in-process stub. LAB-6 extends this with the real
transport, capability flags, and more tools; the in-memory `Client` test pattern
it inherits stays the same.
"""

from __future__ import annotations

from typing import Any, Callable

from fastmcp import FastMCP

from vw_mcp.dispatch import handle_request
from vw_mcp.vs_adapter import StubVsAdapter, VsPort

# Send one request dict to the in-VW companion, get its response dict back.
Companion = Callable[[dict[str, Any]], dict[str, Any]]


def in_process_companion(vs: VsPort) -> Companion:
    """A companion that runs the dispatch logic in-process against ``vs``.

    Stands in for the real TCP-to-Vectorworks transport so the server can be
    driven with Vectorworks closed (tests, local smoke runs).
    """

    def send(request: dict[str, Any]) -> dict[str, Any]:
        return handle_request(request, vs)

    return send


def build_server(companion: Companion) -> FastMCP:
    """Build the MCP server. ``companion`` is the seam to the in-VW listener."""
    mcp: FastMCP = FastMCP("vw-mcp-poc")

    @mcp.tool
    def open_document_filename() -> str:
        """Return the filename of the currently open Vectorworks document."""
        resp = companion({"action": "filename"})
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "companion call failed"))
        if "filename" not in resp:
            raise RuntimeError("companion returned no filename: {!r}".format(resp))
        return resp["filename"]

    return mcp


def build_default_server() -> FastMCP:
    """Server wired to an in-process stub companion — no Vectorworks, no socket.

    Enough to introspect or smoke-run the server locally. LAB-6 replaces the
    stub companion with the real loopback transport to a live VW session.
    """
    return build_server(in_process_companion(StubVsAdapter()))


if __name__ == "__main__":
    build_default_server().run()
