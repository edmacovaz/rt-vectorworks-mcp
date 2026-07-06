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
- **Message path:** JSON over **TCP loopback** (`127.0.0.1:9877`) — proven end-to-end
  on macOS/VW 2026 in [LAB-9]. The MCP server passes messages to the in-VW script and
  gets results back. The remaining transport detail (framing + capability flags on the
  server side, and building it on **FastMCP**) is finalised by [LAB-6]; **[decide in
  LAB-6]** replaces this note once recorded.
- **Lifecycle — modal, turn-taking agent session (proven in [LAB-9]).** The in-VW script
  runs as a **modal dialog "agent session"**: it pumps the loopback socket without
  freezing VW, but it is *turn-taking* — while the session dialog is open the **agent**
  drives VW and manual editing is blocked; closing it hands VW back. This is the only
  safe pure-Python lifecycle (the non-modal Python modes freeze or can't schedule).
  Suitable for the POC's agent-driven extraction/review; **not** for live human+agent
  co-editing — the non-modal native C++ SDK bridge (see `docs/install-workflow.md`) is
  the future upgrade path if that's ever needed.
- **Install / no-paste (proven in [LAB-9]).** The architect starts the session from a
  persistent Plug-in Manager **Command** (type "Command", **not** Tool) placed in the
  user Plug-ins folder; it survives a VW relaunch with no per-session paste. The Command
  holds only a small **stable loader** that reads-and-runs the listener from disk.

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold

The sibling repos in the parent folder are prior art for this shape and worth reading:
`../vectorworks-mcp` (Python listener over TCP) and `../vectorworks-mcp-mako` (Rust +
Unix socket).

## Platform

- **macOS.**
- **Vectorworks 2026.**
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
- `vw_mcp/` — the package (established in [LAB-7]). `vs_adapter.py` is the **`vs` seam**
  (the one place `import vs` happens); `dispatch.py` and `framing.py` are the pure
  companion logic behind it; `server.py` is the FastMCP host server. Companion modules
  (`vs_adapter`, `dispatch`, `framing`) must stay **Python 3.9-compatible** — they run in
  VW's embedded interpreter — even though the host env is newer; `server.py` is host-only.
- `tests/` — the no-Vectorworks safety net (`uv run pytest`).
- `docs/` — `install-workflow.md` (prior-art install research), `vectorworks-glossary.md`
  (domain terms).
- `spike/` — **disposable** [LAB-9] feasibility probes (modal session + persistent
  install), with their own `spike/README.md` test steps. Its pure request/framing logic
  now has a real, tested home in `vw_mcp/`; the spike stays self-contained (runs from a
  downloaded ZIP with no tooling) and is the interim E2E proof until the [LAB-6] scaffold's
  real listener replaces it, at which point the whole `spike/` is removed.

## Testing & verification

The split is protocol/logic tests that run **without Vectorworks open** (the safety net)
vs. an end-to-end path that needs a live Vectorworks handoff (established in [LAB-7]).

**No-Vectorworks safety net — one command:**

```sh
uv run pytest          # excludes the live-VW checks by default
```

This is the fast feedback loop a contributor runs on the dev machine (which has no
Vectorworks). It covers three things without VW: MCP tool behaviour via FastMCP's
in-memory `Client` (schema + dispatch), the server ↔ in-VW message path (newline-JSON
framing round trip), and the companion's dispatch logic against a stubbed `vs`. Lint and
format are `uv run ruff check` / `uv run ruff format`. Tooling: **`uv`** (env/deps/runner,
installed via `brew install uv`), **`pytest`**, **`ruff`** — all *contributor*-side; the
architect never touches them. Deliberately out of scope for the POC: type checker,
coverage gates, tox/nox, snapshot libs, CI.

**What makes the net possible — the `vs` seam.** `vs.*` only exists inside Vectorworks'
embedded Python, so `vw_mcp/vs_adapter.py` is the *single* place `import vs` happens; all
companion logic is typed against its `VsPort` protocol and runs off-VW against a stub.
Keep it that way: never `import vs` outside the adapter.

**Live-VW end-to-end — opt-in, always a handoff.** E2E checks carry `@pytest.mark.e2e`
and are excluded from the default run; opt in with `uv run pytest -m e2e` on a machine
with VW 2026 open. Because the dev machine has no Vectorworks, E2E is always a handoff:
push to GitHub → download onto a macOS + VW 2026 machine → run over loopback → record the
result. That reusable workflow is `README.md` (proven in [LAB-9]). The full MCP round-trip
E2E lands with the [LAB-6] scaffold. Do not claim end-to-end success without Vectorworks
2026 actually open and a round trip proven.

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
