"""Companion dispatch logic, exercised against a stubbed `vs` (no Vectorworks)."""

from vw_mcp.dispatch import CLASSES_SCHEMA_VERSION, handle_line, handle_request
from vw_mcp.vs_adapter import StubVsAdapter, _StubClass


def test_filename_action_returns_open_document_name():
    vs = StubVsAdapter("Harbour Master Plan.vwx")
    resp = handle_request({"action": "filename"}, vs)
    assert resp == {
        "ok": True,
        "action": "filename",
        "filename": "Harbour Master Plan.vwx",
    }


def test_unknown_action_is_a_structured_error():
    resp = handle_request({"action": "nope"}, StubVsAdapter())
    assert resp["ok"] is False
    assert "nope" in resp["error"]


def test_ping_proves_cad_safety_by_doing_the_real_read():
    resp = handle_request(
        {"action": "ping"}, StubVsAdapter("Dock.vwx"), dispatch_mode="dialog"
    )
    assert resp["ok"] is True
    assert resp["cad_api_safe"] is True
    assert resp["transport_only"] is False
    assert resp["dispatch_mode"] == "dialog"
    assert resp["bridge_kind"] == "python_dialog_agent_session"
    assert resp["filename"] == "Dock.vwx"


def test_ping_reports_transport_only_when_the_read_raises():
    # A reachable listener whose CAD call fails is transport-only, not an error:
    # the ping still succeeds (ok=True) but the flags refuse to claim CAD-safety.
    class RaisingVsAdapter:
        def get_open_filename(self):
            raise RuntimeError("vs boom")

    resp = handle_request(
        {"action": "ping"}, RaisingVsAdapter(), dispatch_mode="dialog"
    )
    assert resp["ok"] is True
    assert resp["cad_api_safe"] is False
    assert resp["transport_only"] is True
    assert resp["bridge_kind"] == "python_transport_only"
    assert "filename" not in resp
    assert "vs boom" in resp["error"]


def test_ping_dispatch_mode_defaults_to_unknown_off_vw():
    resp = handle_request({"action": "ping"}, StubVsAdapter())
    assert resp["dispatch_mode"] == "unknown"
    # Off-VW the read still works against the stub, so CAD is nominally safe, but
    # bridge_kind is not the dialog session — it is a generic CAD-safe bridge.
    assert resp["bridge_kind"] == "python_cad_safe"


def test_read_classes_assembles_the_versioned_shape():
    vs = StubVsAdapter(
        classes=[
            _StubClass("None", in_use=True),
            _StubClass("A-WALL", in_use=True, line_weight=25),
            _StubClass("Z-UNUSED", in_use=False),
        ]
    )
    resp = handle_request({"action": "read_classes"}, vs)
    assert resp["ok"] is True
    assert resp["action"] == "read_classes"
    assert resp["schema_version"] == CLASSES_SCHEMA_VERSION
    by_name = {c["name"]: c for c in resp["classes"]}
    # None is a flagged built-in and in use; Z-UNUSED is a vestigial practice class.
    assert by_name["None"]["always_present"] is True
    assert by_name["A-WALL"]["always_present"] is False
    assert by_name["A-WALL"]["in_use"] is True
    assert by_name["Z-UNUSED"]["in_use"] is False
    assert by_name["A-WALL"]["attributes"]["line_weight"] == 25


def test_handle_line_parses_and_dispatches_json():
    resp = handle_line(b'{"action": "filename"}', StubVsAdapter("Untitled"))
    assert resp == {"ok": True, "action": "filename", "filename": "Untitled"}


def test_handle_line_reports_bad_json_without_raising():
    resp = handle_line(b"{not json", StubVsAdapter())
    assert resp["ok"] is False
    assert resp["error"].startswith("bad request:")


def test_handle_line_rejects_non_object_json():
    resp = handle_line(b"[1, 2, 3]", StubVsAdapter())
    assert resp["ok"] is False
    assert "expected a JSON object" in resp["error"]


def test_handle_line_turns_a_failing_vs_call_into_a_structured_error():
    # A live vs.* call can raise inside Vectorworks; it must become an error
    # reply, not crash the listener's pump loop.
    class RaisingVsAdapter:
        def get_open_filename(self):
            raise RuntimeError("vs boom")

    resp = handle_line(b'{"action": "filename"}', RaisingVsAdapter())
    assert resp["ok"] is False
    assert "handler error" in resp["error"]
    assert "vs boom" in resp["error"]
