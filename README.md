# rt-vectorworks-mcp

An internal tool that lets an architect at **Retallack Thompson** drive
**Vectorworks** from an LLM, over the Model Context Protocol (MCP). Purpose-built
for RT — template extraction and automated project review — not a general
Vectorworks automation product.

> **Status: proof of concept.** See [`AGENTS.md`](AGENTS.md) for the
> architecture, principles, and scope.

## Installing the plugin and MCP

The whole tool runs on a single Mac with **Vectorworks 2026**, talking only to
itself over a local connection — nothing is sent over the internet or to another
machine. You need:

- **Vectorworks 2026.**
- **Python 3.10+** for the MCP server. macOS's built-in Python is often older; the
  installer checks and tells you how to get a newer one (e.g.
  `brew install python@3.12`) if you need it. The Vectorworks side uses
  Vectorworks' own Python, so nothing extra is needed there.

> **Coming from the LAB-9 spike?** If you previously installed the throwaway
> spike on this Mac, remove it first so it can't clash with the new session (both
> use the same local port `127.0.0.1:9877`):
> - In Vectorworks: **Tools → Plug-ins → Plug-in Manager**, select the old **VW
>   MCP Spike** command, and delete it (also remove it from the menu via the
>   Workspace editor if you added it there).
> - Optionally delete the spike's leftover folder:
>   `~/Library/Application Support/vw-mcp-spike`.
>
> A machine that never had the spike can skip this.

### 1. Get the code onto the Mac

You don't need a GitHub account or git — a ZIP is enough:

- On the code's GitHub page, switch to the branch you want and click
  **Code → Download ZIP**.
- Double-click to unzip, open the **Terminal** app, and `cd` into the unzipped
  folder. Everything runs from there.

> macOS quirk: unzipping clears the "runnable" flag on scripts, so start them
> with `python3 …` (as shown below) rather than double-clicking.

*(If you already use git, `git clone` then `git checkout <branch>` works too.)*

### 2. Install it

From the unzipped folder, run:

```sh
python3 scripts/install.py
```

This copies the tool to a permanent location (so you can delete the download
afterwards), sets up an isolated Python environment for the MCP server, and copies
a short **loader** snippet to your clipboard. It then prints the remaining steps:

1. In Vectorworks: **Tools → Plug-ins → Plug-in Manager → New → Command** (the
   menu-command type, **not** Tool). Name it **VW MCP Session**.
2. Edit its script, **paste** the loader (already on your clipboard) and save,
   then add it to a menu via **Tools → Workspaces → Edit Current Workspace →
   Menus**. This is a one-time setup; the command then stays in your menu across
   restarts.
3. Connect Claude to the MCP server. The installer prints a ready-made command
   for this — run it in the Terminal, or pass it to your developer to set up. It's
   a one-time step and doesn't change anything in Vectorworks.

### 3. Use it

1. Open a drawing and click the **VW MCP Session** menu command. A small window
   opens and the session starts; Vectorworks stays responsive while it's open, and
   closing the window hands control back to you.
2. In Claude, ask it to check its connection to Vectorworks. A healthy session
   reports the open drawing's file name back and confirms it can read the live
   document.

To check the connection without Claude, run `python3 scripts/vw_ping.py` in the
Terminal while a session is open — it prints whether it reached a healthy session.

### Updating to a new version

Get the new code onto the Mac as in step 1, then run `python3 scripts/install.py`
from the new folder. It refreshes everything in place and recognises that it's an
update: the menu command and the Claude connection stay as they are, so there's
nothing to paste or set up again. To load the new version, close the **VW MCP
Session** window if it's open and start it again from the menu; if the update also
changed the server, restart Claude.

## Working on the code

The code can be changed and checked **without Vectorworks** — the fast feedback
loop for anyone editing it. It covers the MCP tool behaviour, the server ↔
Vectorworks message path, a real local-connection round trip (host client ↔ the
listener's socket server), and the logic behind them, all against a stubbed `vs`.
Live-Vectorworks checks stay opt-in (they use the handoff in step 1) and are
excluded from this run.

[`uv`](https://docs.astral.sh/uv/) manages the environment, dependencies, and
Python:

```sh
brew install uv       # one-time; the only thing you install by hand
uv sync               # creates the venv and installs deps (incl. dev tools)
```

Then, from the repo root:

```sh
uv run pytest         # the checks — no Vectorworks needed
uv run ruff check     # lint
uv run ruff format    # format
```

`uv run pytest` excludes the live-Vectorworks checks by default. To run those
(only on a Mac with VW 2026 open and a session running), use `uv run pytest -m e2e`.

## Key docs

- [`AGENTS.md`](AGENTS.md) — what this is, architecture, principles, scope.
- [`docs/vectorworks-glossary.md`](docs/vectorworks-glossary.md) — Vectorworks
  terms this project touches.
- [`docs/install-workflow.md`](docs/install-workflow.md) — background research on
  how the pieces install and run (from prior-art projects).
