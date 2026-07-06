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
    assert "open_document_filename" in tools
    # A schema is present (FastMCP derives it from the tool signature).
    assert tools["open_document_filename"].inputSchema is not None


def test_tool_call_returns_the_open_filename():
    server = build_server(in_process_companion(StubVsAdapter("Harbour.vwx")))

    async def go():
        async with Client(server) as client:
            return await client.call_tool("open_document_filename", {})

    result = _run(go())
    assert result.data == "Harbour.vwx"
