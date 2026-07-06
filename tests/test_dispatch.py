"""Companion dispatch logic, exercised against a stubbed `vs` (no Vectorworks)."""

from vw_mcp.dispatch import handle_line, handle_request
from vw_mcp.vs_adapter import StubVsAdapter


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
