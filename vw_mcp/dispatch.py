"""Pure request→response logic for the in-Vectorworks companion.

Ported from the LAB-9 spike's ``_handle_request``, but with the ``vs`` calls
pushed behind the :class:`~vw_mcp.vs_adapter.VsPort` seam so the logic is pure
and fully checkable with Vectorworks closed. Read-only only.
"""

from __future__ import annotations

import json
from typing import Any

from vw_mcp.vs_adapter import VsPort


def handle_request(req: dict[str, Any], vs: VsPort) -> dict[str, Any]:
    """Answer one already-parsed request dict against the ``vs`` seam.

    Pure: depends only on ``req`` and ``vs``, never on the real ``vs`` module.
    """
    action = req.get("action")
    if action == "filename":
        return {"ok": True, "action": "filename", "filename": vs.get_open_filename()}
    return {"ok": False, "error": "unsupported action: {!r}".format(action)}


def handle_line(line: bytes, vs: VsPort) -> dict[str, Any]:
    """Parse one wire line as JSON and dispatch it.

    Nothing here raises: malformed input (bad JSON, wrong encoding, non-object)
    and any failure *while answering* (e.g. a ``vs.*`` call raising inside VW)
    both become a structured error response. The listener pumps one line at a
    time on VW's UI thread, so a single bad line or failing CAD call must never
    crash the loop (this mirrors the LAB-9 spike's broad guard).
    """
    try:
        req = json.loads(line.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return {"ok": False, "error": "bad request: {}".format(exc)}
    if not isinstance(req, dict):
        return {"ok": False, "error": "bad request: expected a JSON object"}
    try:
        return handle_request(req, vs)
    except Exception as exc:  # a failing vs.* call must not crash the pump loop
        return {"ok": False, "error": "handler error: {}".format(exc)}
