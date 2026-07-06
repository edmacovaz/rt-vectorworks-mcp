# rt-vectorworks-mcp

An internal tool that lets an architect at **Retallack Thompson** drive
**Vectorworks** from an LLM, over the Model Context Protocol (MCP). Purpose-built
for RT — template extraction and automated project review — not a general
Vectorworks automation product.

> **Status: proof of concept.** See [`AGENTS.md`](AGENTS.md) for the
> architecture, principles, and scope.

## Prerequisites

- **A Mac with Vectorworks 2026.** This is the only place anything can be run
  end to end — the tool works entirely on that one machine.
- The development machine that authors the code has **no Vectorworks** on it, so
  every end-to-end check is handed off to a Vectorworks Mac (below).

## Running it on a Vectorworks Mac

Because the development machine can't run Vectorworks, the code is handed off to
a Mac that has it. This is the durable, repeatable process every check reuses:

1. **The developer publishes the code** to GitHub.
2. **Get the code onto the Vectorworks Mac.** You don't need a GitHub account or
   git — a ZIP is enough:
   - In a browser, open the GitHub page for the code, switch to the branch you
     were asked to test, then click the green **Code → Download ZIP**.
   - Double-click the ZIP to unzip it, open the **Terminal** app, and `cd` into
     the unzipped folder. Everything runs from there, wherever you put it.
   - Nothing needs installing — the checks use the Python that already comes with
     macOS, and Vectorworks provides its own scripting for the rest.

   > macOS quirk: unzipping removes the "runnable" flag from scripts, so start
   > them with `bash …` / `python3 …` (as the instructions show) rather than
   > double-clicking.

   *(If you happen to have git set up, you can `git clone` the repo and
   `git checkout` the branch instead — but the ZIP is the simplest path.)*
3. **Run the checks** for the current implementation — see
   **[Testing this implementation](#testing-this-implementation)** below.
4. **Report the results** back to the developer (recorded on the matching Linear
   issue).

Everything runs on that one Mac and only talks to itself — nothing is sent over
the internet or to another computer. This is also how each architect will
eventually run the tool, on their own machine.

## Testing this implementation

This POC's first implementation is a small, throwaway trial that confirms two
things work on macOS + Vectorworks 2026 before the real tool is built on them.

➡️ **Step-by-step test instructions: [`spike/README.md`](spike/README.md).**

(That trial code lives in [`spike/`](spike/) and is disposable — it will be
removed once the real scaffold lands. The handoff process above is the durable
part.)

## Developing: the no-Vectorworks safety net

Everything above is for the **architect** running the tool on a Vectorworks Mac.
This section is for a **contributor** changing the code — a separate audience with
a separate toolchain that an architect never touches.

The point of this net is fast, trustworthy feedback **with Vectorworks not
running**: the MCP tool behaviour, the server ↔ in-VW message path, and the
companion logic (exercised against a stubbed `vs`) all run on the dev machine.
Live-VW end-to-end checks stay opt-in (see the handoff above) and are excluded
from this run.

One-time setup — [`uv`](https://docs.astral.sh/uv/) manages the environment,
dependencies, and Python for you:

```sh
brew install uv       # one-time; the only thing you install by hand
uv sync               # creates the venv and installs deps (incl. dev tools)
```

Then, from the repo root:

```sh
uv run pytest         # the no-Vectorworks safety net — needs no VW
uv run ruff check     # lint
uv run ruff format    # format
```

`uv run pytest` excludes the live-VW checks by default. To run those (only on a
Mac with VW 2026 open), use `uv run pytest -m e2e`.

## Key docs

- [`AGENTS.md`](AGENTS.md) — what this is, architecture, principles, scope.
- [`docs/vectorworks-glossary.md`](docs/vectorworks-glossary.md) — Vectorworks
  terms this project touches.
- [`docs/install-workflow.md`](docs/install-workflow.md) — background research on
  how the pieces install and run (from prior-art projects).
