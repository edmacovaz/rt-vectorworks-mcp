"""MCP tool behaviour via FastMCP's in-memory Client — schema + dispatch, no VW.

Drives the server through an in-memory `Client` (no subprocess, no stdio, no
socket): the companion is the in-process stub, so a tool call in produces the
expected result out. This is the pattern LAB-6 extends against the real
transport and a live document.
"""

import asyncio

from fastmcp import Client

from vw_mcp.server import build_server, in_process_companion
from vw_mcp.vs_adapter import StubVsAdapter, _StubClass


def _run(coro):
    return asyncio.run(coro)


def _call(server, tool, args=None):
    async def go():
        async with Client(server) as client:
            return await client.call_tool(tool, args or {})

    return _run(go())


def test_tools_are_exposed_with_schemas():
    server = build_server(in_process_companion(StubVsAdapter()))

    async def go():
        async with Client(server) as client:
            return await client.list_tools()

    tools = {t.name: t for t in _run(go())}
    assert "ping" in tools
    assert "read_classes" in tools
    # A schema is present (FastMCP derives it from the tool signature).
    assert tools["ping"].inputSchema is not None
    assert tools["read_classes"].inputSchema is not None


def test_ping_returns_the_filename_plus_capability_flags():
    server = build_server(in_process_companion(StubVsAdapter("Harbour.vwx")))
    result = _call(server, "ping")
    # A real read succeeded through the stub, so the flags say CAD-safe and the
    # real value comes back alongside them.
    assert result.data["filename"] == "Harbour.vwx"
    assert result.data["cad_api_safe"] is True
    assert result.data["transport_only"] is False
    assert result.data["dispatch_mode"] == "stub"


def test_ping_reports_transport_only_when_the_cad_read_fails():
    class RaisingVsAdapter:
        def get_open_filename(self):
            raise RuntimeError("vs unavailable")

    server = build_server(in_process_companion(RaisingVsAdapter()))
    result = _call(server, "ping")
    # Reachable but unsafe for CAD: the flags say so and no filename is claimed.
    assert result.data["cad_api_safe"] is False
    assert result.data["transport_only"] is True
    assert result.data["filename"] is None


# --- read_classes contract --------------------------------------------------
#
# A small hand-authored document model standing in for a real VW read. It is the
# POC's *best guess* at the shape (VW closed); the real values are captured and
# reconciled at the LAB-8 E2E handoff (see the follow-up issue). The contract
# test below pins the *shape*, not VW-proven values.
CONTRACT_CLASSES = [
    _StubClass("None", in_use=True),
    _StubClass("Dimension", in_use=False),
    _StubClass(
        "A-WALL",
        in_use=True,
        pen_fore=(0, 0, 0),
        line_weight=25,
        fill_pattern=1,
        fill_resource=("hatch", "RT Concrete"),
        opacity=100,
        visible=True,
        uses_graphics=True,
    ),
    _StubClass("Z-UNUSED", in_use=False),
]


def _read_classes(server):
    return _call(server, "read_classes").data


def test_read_classes_returns_the_versioned_shape():
    server = build_server(in_process_companion(StubVsAdapter(classes=CONTRACT_CLASSES)))
    data = _read_classes(server)

    assert data["schema_version"] == 1
    names = [c["name"] for c in data["classes"]]
    assert names == ["None", "Dimension", "A-WALL", "Z-UNUSED"]

    by_name = {c["name"]: c for c in data["classes"]}
    wall = by_name["A-WALL"]
    # Every per-class key the contract promises is present and typed.
    assert wall["always_present"] is False
    assert wall["in_use"] is True
    attrs = wall["attributes"]
    assert attrs["pen_fore"] == [0, 0, 0]
    assert isinstance(attrs["pen_back"], list) and len(attrs["pen_back"]) == 3
    assert attrs["line_weight"] == 25
    assert attrs["fill_pattern"] == 1
    assert attrs["fill_resource"] == {"type": "hatch", "name": "RT Concrete"}
    assert attrs["opacity"] == 100
    assert attrs["visible"] is True
    assert attrs["use_graphics"] is True
    # A plain fill has no backing resource.
    assert by_name["None"]["attributes"]["fill_resource"] is None


def test_read_classes_flags_always_present_builtins():
    server = build_server(in_process_companion(StubVsAdapter(classes=CONTRACT_CLASSES)))
    by_name = {c["name"]: c for c in _read_classes(server)["classes"]}
    # None and Dimension are flagged, not silently listed; a practice class is not.
    assert by_name["None"]["always_present"] is True
    assert by_name["Dimension"]["always_present"] is True
    assert by_name["A-WALL"]["always_present"] is False


def test_read_classes_reports_in_use_per_class():
    server = build_server(in_process_companion(StubVsAdapter(classes=CONTRACT_CLASSES)))
    by_name = {c["name"]: c for c in _read_classes(server)["classes"]}
    # The used/vestigial signal: A-WALL has objects, Z-UNUSED is empty cruft.
    assert by_name["A-WALL"]["in_use"] is True
    assert by_name["Z-UNUSED"]["in_use"] is False


def test_read_classes_degrades_one_unreadable_class_without_dropping_it():
    # A class whose attribute read raises must still appear, with attributes null
    # and a note — the rest of the list is unaffected.
    class OneBadClass(StubVsAdapter):
        def class_pen_fore(self, name):
            if name == "A-WALL":
                raise RuntimeError("vs attr boom")
            return super().class_pen_fore(name)

    server = build_server(in_process_companion(OneBadClass(classes=CONTRACT_CLASSES)))
    by_name = {c["name"]: c for c in _read_classes(server)["classes"]}
    assert by_name["A-WALL"]["attributes"] is None
    assert "vs attr boom" in by_name["A-WALL"]["attributes_error"]
    # A sibling class is untouched.
    assert by_name["None"]["attributes"] is not None
