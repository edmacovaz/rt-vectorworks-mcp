# Test-handoff workflow (macOS + VW 2026)

> **This is the durable deliverable of [LAB-9].** The dev machine has **no
> Vectorworks installed**, so every end-to-end check runs on a separate
> **macOS + Vectorworks 2026** machine. This README is the repeatable loop for
> getting code onto that machine, running the stack over loopback, and carrying
> the result back. Later E2E checks ([LAB-6], [LAB-8]) reuse it.

The topology is fixed: **single machine, loopback only.** The architect runs
the entire stack on their own Vectorworks machine — this is the deployment
model, not just a test rig, so there is never any cross-machine networking or
auth in scope. The only cross-machine step is the *dev-time handoff of code*
below, over git.

Prior-art research this builds on: [`install-workflow.md`](install-workflow.md).

## Roles

- **Dev box** (this machine): authoring only. Writes code, pushes branches.
  Cannot run Vectorworks.
- **VW box**: a macOS machine with Vectorworks 2026. Pulls the branch, runs the
  stack over loopback, reports results.

## The handoff loop

1. **Push (dev box).** Commit and push the branch under test.
   ```
   git push -u origin <branch>
   ```
2. **Pull (VW box).** Clone once, then pull the branch:
   ```
   git clone <repo-url> rt-vectorworks-mcp   # first time only
   cd rt-vectorworks-mcp
   git fetch origin && git checkout <branch> && git pull
   ```
   No dependencies are needed for the LAB-9 spike — it is stdlib-only Python on
   both ends, and Vectorworks supplies the `vs.*` API. (Later scaffolds add a
   `pip install`; see their own docs.)
3. **Run** the checks on the VW box (below).
4. **Capture back.** Record the outcome on the Linear issue being validated
   (the issue is the spec container — see `AGENTS.md`). Paste the terminal
   output and note UI responsiveness. Refuting an assumption is a valid result.

## What LAB-9 validates

Two go/no-go feasibility probes. Both prove macOS/VW 2026 assumptions that the
Windows-only prior art cannot. The spike code lives in [`../spike/`](../spike/)
and is **disposable** — [LAB-6] deletes it once the findings land.

### Probe A — modal-dialog socket pump

Proves a modal-dialog "agent session" can pump a loopback socket **without
freezing VW's UI** and answer one read-only `vs.*` call (`vs.GetFName()`, the
open document's filename).

On the VW box:

1. Open Vectorworks 2026 to any document (even a blank one).
2. Load the listener: **Resource Manager** (`Cmd+R`) → **New Resource** →
   **Script** → **Python** → paste the entire contents of
   [`spike/vw_modal_listener.py`](../spike/vw_modal_listener.py) → **run**.
3. A modal **"VW MCP Spike"** dialog opens and stays open, listening on
   `127.0.0.1:9877`.
4. **Confirm VW is not frozen**: with the dialog open, pan/zoom the document —
   the UI should stay responsive.
5. In a terminal on the same machine:
   ```
   python3 spike/poke.py
   ```
6. Click **Stop** (or close the dialog) to end the session and get VW back.

**PASS** if: the dialog opens, VW stays responsive while it is open, and
`poke.py` prints `PASS: round trip OK. Open document filename = ...` with the
real filename. **FAIL** (a valid result) if the UI freezes or no real value
comes back.

### Probe B — persistent, no-paste install

Proves a setup step can place a menu command that **survives a VW relaunch**
and starts the session with **no per-session paste**. It uses a *stable loader*
(the menu command holds a few lines that read-and-run the listener from disk),
so listener logic can change without re-editing the menu command.

On the VW box:

1. Open Vectorworks 2026 once (so it creates its user folder).
2. Prepare the loader:
   ```
   ./spike/persistent_probe/install.sh          # defaults to VW 2026
   ```
   This bakes the absolute listener path into a loader, copies it to the
   clipboard, and reports the macOS Plug-ins path
   (`~/Library/Application Support/Vectorworks/2026/Plug-ins`) — confirming that
   path is part of the probe.
3. Create the menu command **once** (Plug-in Manager → New → Menu Command →
   paste the loader → Save; then add it to the workspace). The script prints the
   exact steps.
4. **Quit and reopen Vectorworks 2026** — this is the persistence test.
5. Click the **"VW MCP Spike"** menu command. The modal session should open with
   no pasting. Then run `python3 spike/poke.py` to confirm the round trip
   (same as Probe A).

**PASS** if: after the relaunch the menu command is still present and starts the
session with no paste. **FAIL** (a valid result) if it does not survive the
relaunch, or the macOS folder path/packaging differs on VW 2026.

## Recording the result

Post both probe outcomes as a comment on [LAB-9] (and flag them for [LAB-6]):

- Probe A: PASS/FAIL — did the UI stay responsive? what filename came back?
- Probe B: PASS/FAIL — did the menu command survive relaunch and run without
  paste? what was the actual Plug-ins path?

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold
[LAB-8]: https://linear.app/edmacovaz/issue/LAB-8/document-manifest-tool
