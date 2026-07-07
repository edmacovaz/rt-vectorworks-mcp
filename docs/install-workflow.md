# Vectorworks MCP — install workflow research

> **Status: research notes** for the POC. Distilled from two prior-art sibling
> repos — `../vectorworks-mcp` (Python MCP server over TCP) and
> `../vectorworks-mcp-mako` (Rust server + C++ VCOM plugin over a Unix socket) —
> and mapped onto this project's target (**macOS, Vectorworks 2026, Python
> end-to-end**). Where a decision is still open it is called out, not guessed.

## The core shape (common to all approaches)

A Vectorworks MCP is **two processes that must both be running**, plus a
client-config step:

1. **MCP server** — a stdio process the MCP client (Claude Code / Codex)
   launches. Holds no CAD state; it forwards tool calls.
2. **Companion inside Vectorworks** — the only thing that can touch the document
   (`vs.*` API). Listens on a local socket.
3. **Bridge** — TCP or Unix socket on loopback between them.

```
MCP client ──stdio──> MCP server ──local socket──> companion inside VW ──> vs.* API
```

Two prior-art variants:

| | `vectorworks-mcp` (Bhavesh) | `vectorworks-mcp-mako` |
|---|---|---|
| Server | Python `server.py` (FastMCP) | Rust binary |
| Companion | `vw_listener.py` pasted into VW | Compiled C++ VCOM plugin (`.vwlibrary`) |
| Transport | TCP `127.0.0.1:9877` (JSON) | Unix socket `/tmp/vw-mcp-bridge.sock` |
| Install effort | paste a script + register MCP | build C++ plugin + Rust, drop into Plug-ins |
| Platform | Windows-first (PowerShell) | Mac/Windows |

This POC targets the **Python end-to-end** path (left column) — no compiler, no
SDK needed.

## Canonical install sequence (Python path)

1. **Host prereqs** — Python 3.x, git, an stdio MCP client, Vectorworks
   installed.
2. **Repo + deps** — clone, `pip install -r requirements.txt` (FastMCP).
3. **Register MCP server with the client** — add a stdio entry to `.mcp.json` /
   `~/.claude.json` with env for host/port/timeout.
4. **Generate launcher + stable loader** — setup emits a full launcher (absolute
   paths, `VW_MCP_MODE=dialog`) plus a tiny **stable loader** whose only job is
   to read-and-run the launcher from disk.
5. **Load companion in VW** — Resource Manager (`Cmd/Ctrl+R`) → New Resource →
   Script → Python → paste **only the loader** → run. A modal "VW MCP Listener"
   dialog stays open for the session. (Optionally a persistent menu command via
   Plug-in Manager.)
6. **Verify end-to-end** — call `ping`; healthy = `dispatch_mode=dialog`,
   `cad_api_safe=true`, `transport_only=false`. Raw socket reachability alone is
   **not** sufficient.

(There is also an optional long-term **native C++ SDK bridge** — a non-modal
upgrade path, not part of the base install.)

## Hard-won lessons worth stealing

- **The listener must not block VW's UI.** Foreground/background/timer modes
  freeze or can't schedule — all marked guarded/diagnostic-only. The only safe
  pure-Python mode is a **modal dialog "agent session"** that pumps the socket
  while open; close it to get VW back. This is the biggest design constraint and
  the thing the POC's first round trip must validate.
- **Loader indirection prevents stale-code freezes** — never paste the full
  listener directly; the two-line loader lets you regenerate logic without
  re-pasting into VW.
- **`transport_only=true` is a real failure mode** — a listener can answer
  `ping` yet be unsafe for CAD calls. Ping should return capability flags, not
  just "ok".
- **Menu/UI paths drift by version and OS.** All prior-art tested paths are
  **Windows** (`py -3`, PowerShell, winget, `install.ps1`) — this project is
  **macOS + VW 2026**, so re-verify menu paths and interpreter invocation
  independently. Treat their scripts as reference logic, not runnable.
- **Client registration is fiddly** — `claude mcp add` assumes the `claude` CLI
  is on PATH; the reliable fallback is editing `~/.claude.json` / project
  `.mcp.json` directly.

## Decisions (settled in LAB-6)

These were the POC's open decisions; LAB-6 settled and shipped them:

- **Transport: DECIDED — TCP loopback** `127.0.0.1:9877`, newline-delimited JSON,
  host server on **FastMCP** (`vw_mcp/server.py`, `tcp_companion`).
- **Lifecycle: DECIDED — modal-dialog agent session** with a stable-loader
  indirection (`vw_mcp/listener.py`; installed by `scripts/install.py`).
- **First round trip: DONE — `ping`** returns the open document's filename plus
  *proven* capability flags (`cad_api_safe` / `transport_only` / `dispatch_mode` /
  `bridge_kind`) from a live VW 2026 document.

Still open (deliberately deferred): **no-paste auto-registration** of the menu
Command (the loader is still pasted once) — tracked in **LAB-11**.
