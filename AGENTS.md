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
MCP client ──stdio──> Python MCP server ──[transport: decide in POC]──> Python script in Vectorworks ──> Vectorworks Python SDK/API
```

- **Host:** Python MCP server, spoken to over stdio by the MCP client.
- **Vectorworks side:** a Python script running inside Vectorworks, using the
  Vectorworks **Python SDK/API** (`vs.*`) to read/write the document.
- **Message path:** the MCP server passes messages to the running in-VW script and gets
  results back. The exact transport and script-loading/lifecycle model are the first
  thing the POC pins down — start with the simplest round trip (fetch some data from a
  live Vectorworks file) and let that drive the decision.

The sibling repos in the parent folder are prior art for this shape and worth reading:
`../vectorworks-mcp` (Python listener over TCP) and `../vectorworks-mcp-mako` (Rust +
Unix socket).

## Platform

- **macOS.**
- **Vectorworks 2026.**

## Project layout

**[decide in POC]** — grows as the scaffold lands (MCP server, in-VW script, skills,
tests). Keep this section current as directories appear.

## Testing & verification

**[decide in POC]** — the intended split is protocol/logic tests that run **without
Vectorworks open** (the safety net) vs. an end-to-end path that needs a live Vectorworks
handoff. Fill in exact commands once they exist. Do not claim end-to-end success without
Vectorworks 2026 actually open and a round trip proven.

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
