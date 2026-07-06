"""Example live-Vectorworks check — the opt-in `e2e` marker convention.

Excluded from the default `uv run pytest`; opt in with `uv run pytest -m e2e` on
a Mac with VW 2026 open. Real e2e tests (LAB-6) will drive the full MCP server →
loopback → live-VW round trip. Until that transport lands, this pins down the
gate: an e2e test only means anything inside Vectorworks' Python, so it skips
cleanly elsewhere rather than failing.
"""

import pytest

from vw_mcp.vs_adapter import VectorworksAdapter

pytestmark = pytest.mark.e2e


def test_live_open_document_filename():
    try:
        adapter = VectorworksAdapter()
    except RuntimeError:
        pytest.skip("not running inside Vectorworks (vs module unavailable)")
    filename = adapter.get_open_filename()
    assert isinstance(filename, str) and filename
