# Agent Instructions — rt-vectorworks-mcp

> **Status: POC.** This repo is at the proof-of-concept stage (Linear milestone "POC").
> The POC exists to surface the key decisions by building one simple round trip; where
> something isn't decided yet it is marked **[decide in POC]**, not guessed.

## What this is

A Model Context Protocol (MCP) server that lets an architect at **Retallack Thompson
(RT)** drive **Vectorworks** from an LLM. It is a purpose-built internal tool, not a
general-purpose Vectorworks automation product. Two target use cases:

1. **Template extraction** — read a series of existing RT project files and pull out
   their classes and sheets to build a general-purpose Vectorworks **template file**.
2. **Automated review** — check project files against RT checklists/skills for auditing
   and handover preparation.

Everything in the POC serves proving one of these end to end at small scale.

## Architecture (proposed)

```
MCP client ──stdio──> Python MCP server ──TCP loopback 127.0.0.1:9877──> Python script in Vectorworks ──> Vectorworks Python SDK/API
```

- **Host:** Python MCP server, spoken to over stdio by the MCP client.
- **Vectorworks side:** a Python script running inside Vectorworks, using the
  Vectorworks **Python SDK/API** (`vs.*`) to read/write the document.
- **Message path (decided in [LAB-6]).** JSON over **TCP loopback** (`127.0.0.1:9877`),
  **newline-delimited** — one JSON object per line — with the host server built on
  **FastMCP**. The host exposes one read-only tool, `vw_ping`: it forwards a request to
  the in-VW listener and shapes the reply, which carries a real `vs.*` value (the open
  document's filename) **plus capability flags** (`cad_api_safe` / `transport_only` /
  `dispatch_mode` / `bridge_kind`). The flags are *proven*, not declared — the listener
  only reports `cad_api_safe=true` when the real read just succeeded — so a healthy CAD
  session is distinguishable from a socket-reachable but CAD-unsafe (`transport_only`)
  one.
- **Lifecycle — modal, turn-taking agent session (proven in [LAB-9]).** The in-VW script
  runs as a **modal dialog "agent session"**: it pumps the loopback socket without
  freezing VW, but it is *turn-taking* — while the session dialog is open the **agent**
  drives VW and manual editing is blocked; closing it hands VW back. This is the only
  safe pure-Python lifecycle (the non-modal Python modes freeze or can't schedule).
  Suitable for the POC's agent-driven extraction/review; **not** for live human+agent
  co-editing — the non-modal native C++ SDK bridge (see `docs/install-workflow.md`) is
  the future upgrade path if that's ever needed.
- **Install (productionised in [LAB-6]).** `scripts/install.py` (system `python3`) copies
  the `vw_mcp` package + listener to a stable location (`~/Library/Application
  Support/vw-mcp`), builds an isolated venv for the host server, generates the **stable
  loader** (paths baked in) and prints the MCP registration command. The architect starts
  the session from a persistent Plug-in Manager **Command** (type "Command", **not** Tool)
  that holds only that loader, which reads-and-runs the listener from disk. The Command
  survives a VW relaunch. **Residual manual step:** the loader is still pasted **once**
  into the Command (and added to a workspace menu); removing that last paste — full
  no-paste auto-registration — is [LAB-11]. The installer deliberately does **not** edit
  the MCP client's config; it prints the launch command instead, to avoid coupling to the
  client's evolving setup.

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold
[LAB-11]: https://linear.app/edmacovaz/issue/LAB-11/no-paste-plugin-install-auto-register-the-vw-menu-command

The sibling repos in the parent folder are prior art for this shape and worth reading:
`../vectorworks-mcp` (Python listener over TCP) and `../vectorworks-mcp-mako` (Rust +
Unix socket).

## Platform

- **macOS.**
- **Vectorworks 2026.**
- **Split interpreter.** The in-VW **listener** runs in VW 2026's embedded **Python 3.9**
  (so `vs_adapter` / `dispatch` / `framing` / `listener` must stay 3.9-compatible), but the
  host **MCP server** runs on **FastMCP, which needs Python 3.10+**. macOS's system
  `python3` is often 3.9, so `scripts/install.py` discovers a 3.10+ interpreter for the
  server's venv and stops with a clear message if there isn't one.
- **In-VW Python defaults to ASCII.** VW 2026's embedded Python 3.9 uses ASCII as its
  default text encoding, so reading any file with non-ASCII content raises
  `UnicodeDecodeError`. Always pass `encoding="utf-8"` explicitly when opening files
  from inside Vectorworks (proven in [LAB-9]).

## Project layout

Grows as the scaffold lands (MCP server, in-VW script, skills) — keep current as
directories appear.

- `README.md` — entry point + the reusable **test-handoff workflow** (run the stack on a
  macOS + VW 2026 machine) and the contributor **no-Vectorworks** test commands.
- `pyproject.toml` — project + dev tooling (`uv`-managed): deps, `pytest` config (the
  `e2e` marker, excluded by default), `ruff` config. `uv.lock` pins it.
- `vw_mcp/` — the package. `vs_adapter.py` is the **`vs` seam** (the one place `vs.*`
  *reads* happen); `dispatch.py` and `framing.py` are the pure companion logic behind it;
  `listener.py` is the in-VW runtime (modal agent-session dialog + non-blocking socket
  pump) that imports that tested core; `server.py` is the FastMCP host server. The
  companion modules `vs_adapter` / `dispatch` / `framing` / `listener` run in VW's embedded
  interpreter, so they must stay **Python 3.9-compatible**; `server.py` is host-only (and
  the only module that imports `fastmcp`).
- `scripts/` — architect-side, system-`python3`, no `uv`: `install.py` (the one-time
  installer) and `vw_ping.py` (stdlib smoke check for a live session over loopback).
- `tests/` — the no-Vectorworks safety net (`uv run pytest`).
- `docs/` — `install-workflow.md` (install research + the recorded [LAB-6] decisions),
  `vectorworks-glossary.md` (domain terms).

## Testing & verification

The split is protocol/logic tests that run **without Vectorworks open** (the safety net)
vs. an end-to-end path that needs a live Vectorworks handoff (established in [LAB-7]).

**No-Vectorworks safety net — one command:**

```sh
uv run pytest          # excludes the live-VW checks by default
```

This is the fast feedback loop a contributor runs on the dev machine (which has no
Vectorworks). It covers, without VW: MCP tool behaviour via FastMCP's in-memory `Client`
(`vw_ping` schema + capability flags), the server ↔ in-VW message path (newline-JSON
framing round trip), a **real loopback transport round trip** (`tcp_companion` ↔ the
listener's `SocketPump`, with a stubbed `vs`), and the companion's dispatch logic. Lint and
format are `uv run ruff check` / `uv run ruff format`. Tooling: **`uv`** (env/deps/runner,
installed via `brew install uv`), **`pytest`**, **`ruff`** — all *contributor*-side; the
architect never touches them. Deliberately out of scope for the POC: type checker,
coverage gates, tox/nox, snapshot libs, CI.

**What makes the net possible — the `vs` seam.** `vs.*` only exists inside Vectorworks'
embedded Python, so all companion **logic** (`dispatch`, `framing`, and the `SocketPump`
in `listener`) is typed against the `VsPort` protocol and runs off-VW against a stub —
never touching `vs` directly. `vs_adapter.py` is the single place `vs` **reads** happen.
The one sanctioned exception is `listener.run()`, the VW-UI boundary: it uses `vs` for the
modal-dialog calls (which have no read semantics and can't run off-VW anyway), while its
CAD reads still flow through the adapter. So: keep `vs` reads in the adapter, and never
import `vs` in pure logic.

**Live-VW end-to-end — opt-in, always a handoff.** E2E checks carry `@pytest.mark.e2e`
and are excluded from the default run; opt in with `uv run pytest -m e2e` on a machine
with VW 2026 open **and a session running**. The full MCP round-trip E2E landed with the
[LAB-6] scaffold: `tests/test_e2e_example.py` drives the real host transport → loopback →
live listener round trip and asserts a CAD-safe session (it skips cleanly when nothing is
reachable). `scripts/vw_ping.py` is the quick stdlib smoke equivalent for the handoff.
Because the dev machine has no Vectorworks, E2E is always a handoff: push to GitHub →
download onto a macOS + VW 2026 machine → install → open a session → run over loopback →
record the result (workflow in `README.md`, proven in [LAB-9]). Do not claim end-to-end
success without Vectorworks 2026 actually open and a round trip proven.

[LAB-7]: https://linear.app/edmacovaz/issue/LAB-7/verify-mcp-server-and-companion-logic-changes-without-opening

## Working conventions

- **Project management:** git + Linear. The Linear issue is the spec container — the
  spec and plan live on the issue, not in repo markdown. No in-repo
  `spec.md` / `plan.md` / `tasks.md`.
- **Commits:** imperative summary with the Linear issue id in parentheses, e.g.
  `Add MCP round-trip scaffold (LAB-6)`.
- **Safety:** any tool that modifies a user's Vectorworks document is destructive —
  ask before running it against a real project file. Prefer read-only calls in the POC.

## Domain reference

Vectorworks terms an agent must get right (classes, design layers, sheet layers,
viewports, templates, symbols) are summarised in
[`docs/vectorworks-glossary.md`](docs/vectorworks-glossary.md). Expand it from the
Vectorworks 2026 SDK docs as needed.
