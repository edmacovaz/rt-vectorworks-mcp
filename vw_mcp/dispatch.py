"""Pure request→response logic for the in-Vectorworks companion.

Ported from the LAB-9 spike's ``_handle_request``, but with the ``vs`` calls
pushed behind the :class:`~vw_mcp.vs_adapter.VsPort` seam so the logic is pure
and fully checkable with Vectorworks closed. Read-only only.
"""

from __future__ import annotations

import json
from typing import Any

from vw_mcp.vs_adapter import VsPort

# Version stamped on every read_classes reply. Bump on any *breaking* change to
# the class shape so downstream (multi-file, write) capabilities can rely on it.
CLASSES_SCHEMA_VERSION = 1

# Classes Vectorworks always creates in a fresh document. Flagged, not hidden, so
# a consumer can tell built-ins apart from a practice's own classes.
ALWAYS_PRESENT_CLASSES = frozenset({"None", "Dimension"})


def _bridge_kind(dispatch_mode: str, cad_api_safe: bool) -> str:
    """Name the runtime bridge from its proven capability (mirrors prior art)."""
    if not cad_api_safe:
        return "python_transport_only"
    if dispatch_mode == "dialog":
        return "python_dialog_agent_session"
    return "python_cad_safe"


def _ping(vs: VsPort, dispatch_mode: str) -> dict[str, Any]:
    """Capability probe: *prove* CAD-safety by actually doing the read.

    A reachable listener can still be unsafe for ``vs.*`` calls
    (``transport_only=true`` — see AGENTS.md), so the flags must be earned, not
    declared: we attempt the real read and let its outcome set ``cad_api_safe``.
    Either way the ping itself succeeded (``ok=true``) — a transport-only session
    is a valid, reportable state, not an error.
    """
    try:
        filename = vs.get_open_filename()
    except Exception as exc:  # reachable over the socket, but the CAD call failed
        return {
            "ok": True,
            "action": "ping",
            "dispatch_mode": dispatch_mode,
            "cad_api_safe": False,
            "transport_only": True,
            "bridge_kind": _bridge_kind(dispatch_mode, False),
            "error": "cad read failed: {}".format(exc),
        }
    return {
        "ok": True,
        "action": "ping",
        "dispatch_mode": dispatch_mode,
        "cad_api_safe": True,
        "transport_only": False,
        "bridge_kind": _bridge_kind(dispatch_mode, True),
        "filename": filename,
    }


def _class_attributes(vs: VsPort, name: str) -> dict[str, Any]:
    """Assemble one class's graphic attributes from the thin seam reads.

    Resource-backed fills (hatch/gradient/tile/image) are captured *by reference*
    — ``{"type", "name"}`` — never by serialising the resource. Markers and 3D
    textures are deliberately out of this v1 set (compound/resource-deep, the
    same line the fill reference draws); add them behind a schema bump if needed.
    """
    fill_resource = vs.class_fill_resource(name)
    return {
        "pen_fore": list(vs.class_pen_fore(name)),
        "pen_back": list(vs.class_pen_back(name)),
        "line_weight": vs.class_line_weight(name),
        "line_style": vs.class_line_style(name),
        "fill_fore": list(vs.class_fill_fore(name)),
        "fill_back": list(vs.class_fill_back(name)),
        "fill_pattern": vs.class_fill_pattern(name),
        "fill_resource": (
            None
            if fill_resource is None
            else {"type": fill_resource[0], "name": fill_resource[1]}
        ),
        "opacity": vs.class_opacity(name),
        "visible": vs.class_visible(name),
        "use_graphics": vs.class_uses_graphics(name),
    }


def _read_classes(vs: VsPort) -> dict[str, Any]:
    """Read the document's class list into the stable, versioned shape.

    One traversal fixes which classes are in use; each class is then enumerated
    with its always-present flag and attributes. A single class whose attribute
    read fails degrades to ``attributes: null`` (plus a note) rather than sinking
    the whole list — the same resilience the pump loop gives a failing call.
    """
    in_use = vs.classes_in_use()
    classes = []
    for index in range(1, vs.class_count() + 1):
        name = vs.class_name_at(index)
        entry: dict[str, Any] = {
            "name": name,
            "always_present": name in ALWAYS_PRESENT_CLASSES,
            "in_use": name in in_use,
        }
        try:
            entry["attributes"] = _class_attributes(vs, name)
        except Exception as exc:
            entry["attributes"] = None
            entry["attributes_error"] = "attribute read failed: {}".format(exc)
        classes.append(entry)
    return {
        "ok": True,
        "action": "read_classes",
        "schema_version": CLASSES_SCHEMA_VERSION,
        "classes": classes,
    }


def handle_request(
    req: dict[str, Any], vs: VsPort, dispatch_mode: str = "unknown"
) -> dict[str, Any]:
    """Answer one already-parsed request dict against the ``vs`` seam.

    Pure: depends only on ``req``, ``vs``, and the listener's ``dispatch_mode``,
    never on the real ``vs`` module. ``dispatch_mode`` is what the live listener
    knows about its own lifecycle (``"dialog"`` for the modal agent session);
    off-VW callers leave it ``"unknown"``.
    """
    action = req.get("action")
    if action == "filename":
        return {"ok": True, "action": "filename", "filename": vs.get_open_filename()}
    if action == "ping":
        return _ping(vs, dispatch_mode)
    if action == "read_classes":
        return _read_classes(vs)
    return {"ok": False, "error": "unsupported action: {!r}".format(action)}


def handle_line(
    line: bytes, vs: VsPort, dispatch_mode: str = "unknown"
) -> dict[str, Any]:
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
        return handle_request(req, vs, dispatch_mode)
    except Exception as exc:  # a failing vs.* call must not crash the pump loop
        return {"ok": False, "error": "handler error: {}".format(exc)}
