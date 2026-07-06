"""The newline-delimited-JSON wire format: line boundaries + round trip."""

from vw_mcp.dispatch import handle_line
from vw_mcp.framing import LineFramer, encode_message
from vw_mcp.vs_adapter import StubVsAdapter


def test_single_complete_line():
    assert LineFramer().feed(b'{"a": 1}\n') == [b'{"a": 1}']


def test_multiple_lines_in_one_chunk():
    assert LineFramer().feed(b"one\ntwo\nthree\n") == [b"one", b"two", b"three"]


def test_partial_line_is_held_until_the_rest_arrives():
    framer = LineFramer()
    assert framer.feed(b'{"acti') == []
    assert framer.feed(b'on": "filename"}\n') == [b'{"action": "filename"}']


def test_line_split_across_the_newline_boundary():
    framer = LineFramer()
    assert framer.feed(b"first") == []
    assert framer.feed(b"\nsecond\n") == [b"first", b"second"]


def test_blank_lines_are_dropped():
    assert LineFramer().feed(b"\n\nx\n\n") == [b"x"]


def test_round_trip_encode_then_reframe_and_dispatch():
    # Encode a request as a wire line, push it through the framer in awkward
    # chunks, and dispatch the reassembled line — the full message path, no VW.
    wire = encode_message({"action": "filename"})
    framer = LineFramer()
    lines = framer.feed(wire[:5]) + framer.feed(wire[5:])
    assert len(lines) == 1
    resp = handle_line(lines[0], StubVsAdapter("Dock.vwx"))
    assert resp == {"ok": True, "action": "filename", "filename": "Dock.vwx"}
