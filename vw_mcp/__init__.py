"""rt-vectorworks-mcp — MCP server + in-Vectorworks companion (POC).

Package layout mirrors the `vs` seam that makes off-Vectorworks testing possible:

- `vs_adapter` — the *only* module that imports Vectorworks' `vs`. Everything
  else depends on the `VsPort` seam, so it runs and is tested off-VW.
- `dispatch` — pure request→response logic, typed against `VsPort`.
- `framing` — the newline-delimited-JSON wire format (line boundaries + encoding).
- `server` — the FastMCP server exposing the read-only tool(s).

The companion modules (`vs_adapter`, `dispatch`, `framing`) run inside
Vectorworks 2026's embedded Python 3.9, so they must stay 3.9-compatible even
though the host env is newer. `server` runs only on the host (FastMCP) side.
"""
