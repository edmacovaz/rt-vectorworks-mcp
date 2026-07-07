"""Live-Vectorworks end-to-end check — the opt-in `e2e` marker.

Excluded from the default `uv run pytest`; opt in with `uv run pytest -m e2e` on
a Mac with VW 2026 open **and a VW MCP session running** (the modal listener,
started from the installed Plug-in Manager Command). It drives the real host
transport → loopback → live listener round trip and asserts the capability flags
of a healthy CAD session. It skips cleanly when no session is reachable, so it
never fails off-Vectorworks — a real round trip is the only thing that makes it
pass (see AGENTS.md: E2E is never claimed without one).
"""

import pytest

from vw_mcp.server import DEFAULT_HOST, DEFAULT_PORT, tcp_companion

pytestmark = pytest.mark.e2e


def test_live_round_trip_reports_a_cad_safe_session():
    send = tcp_companion(DEFAULT_HOST, DEFAULT_PORT, timeout=5.0)
    try:
        resp = send({"action": "ping"})
    except (OSError, RuntimeError):
        # OSError = nothing listening; RuntimeError = something answered but
        # dropped the connection / spoke garbage (a stale or half-open peer).
        # Either way there's no live session to assert against — skip cleanly.
        pytest.skip(
            "no VW MCP session reachable on {}:{} — open one from the "
            "installed VW menu Command".format(DEFAULT_HOST, DEFAULT_PORT)
        )
    assert resp["ok"] is True
    assert resp["cad_api_safe"] is True
    assert resp["transport_only"] is False
    assert resp["dispatch_mode"] == "dialog"
    assert isinstance(resp["filename"], str) and resp["filename"]


def test_live_read_classes_returns_the_documents_classes():
    send = tcp_companion(DEFAULT_HOST, DEFAULT_PORT, timeout=5.0)
    try:
        resp = send({"action": "read_classes"})
    except (OSError, RuntimeError):
        pytest.skip(
            "no VW MCP session reachable on {}:{} — open one from the "
            "installed VW menu Command".format(DEFAULT_HOST, DEFAULT_PORT)
        )
    assert resp["ok"] is True
    assert resp["schema_version"] == 1
    classes = resp["classes"]
    assert isinstance(classes, list) and classes
    names = {c["name"] for c in classes}
    # Vectorworks always creates these, and read_classes must flag them.
    assert {"None", "Dimension"} <= names
    for c in classes:
        assert isinstance(c["name"], str)
        assert isinstance(c["always_present"], bool)
        assert isinstance(c["in_use"], bool)
        # Attributes read succeeded (dict) or degraded cleanly (null) — never absent.
        assert "attributes" in c
    always = {c["name"] for c in classes if c["always_present"]}
    assert always == {"None", "Dimension"} & names
