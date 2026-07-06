"""MCP tool behaviour via FastMCP's in-memory Client — schema + dispatch, no VW.

Drives the server through an in-memory `Client` (no subprocess, no stdio, no
socket): the companion is the in-process stub, so a tool call in produces the
expected result out. This is the pattern LAB-6 extends against the real
transport and a live document.
"""

import asyncio

from fastmcp import Client

from vw_mcp.server import build_server, in_process_companion
from vw_mcp.vs_adapter import StubVsAdapter


def _run(coro):
    return asyncio.run(coro)


def test_tool_is_exposed_with_a_schema():
    server = build_server(in_process_companion(StubVsAdapter()))

    async def go():
        async with Client(server) as client:
            return await client.list_tools()

    tools = {t.name: t for t in _run(go())}
    assert "vw_ping" in tools
    # A schema is present (FastMCP derives it from the tool signature).
    assert tools["vw_ping"].inputSchema is not None


def test_vw_ping_returns_the_filename_plus_capability_flags():
    server = build_server(in_process_companion(StubVsAdapter("Harbour.vwx")))

    async def go():
        async with Client(server) as client:
            return await client.call_tool("vw_ping", {})

    result = _run(go())
    # A real read succeeded through the stub, so the flags say CAD-safe and the
    # real value comes back alongside them.
    assert result.data["filename"] == "Harbour.vwx"
    assert result.data["cad_api_safe"] is True
    assert result.data["transport_only"] is False
    assert result.data["dispatch_mode"] == "stub"


def test_vw_ping_reports_transport_only_when_the_cad_read_fails():
    class RaisingVsAdapter:
        def get_open_filename(self):
            raise RuntimeError("vs unavailable")

    server = build_server(in_process_companion(RaisingVsAdapter()))

    async def go():
        async with Client(server) as client:
            return await client.call_tool("vw_ping", {})

    result = _run(go())
    # Reachable but unsafe for CAD: the flags say so and no filename is claimed.
    assert result.data["cad_api_safe"] is False
    assert result.data["transport_only"] is True
    assert result.data["filename"] is None
