# Test-handoff workflow (macOS + Vectorworks 2026)

> **This is the durable deliverable of [LAB-9].** The development machine has
> **no Vectorworks installed**, so every end-to-end check has to run on a
> separate Mac that has **Vectorworks 2026**. This is the step-by-step for
> getting the code onto that Mac, running the checks, and reporting the result
> back. Later checks ([LAB-6], [LAB-8]) reuse this same workflow.

Everything runs on that one Vectorworks Mac and only talks to itself — nothing
is sent over the internet or to another computer. (This is also how each
architect will eventually run the tool: entirely on their own machine.) The
only step that moves between computers is copying the code across, covered
below.

Background research this builds on: [`install-workflow.md`](install-workflow.md).

## Two roles

- **The developer** writes the code and publishes it to GitHub. (Nothing to do
  on the Vectorworks Mac for this part.)
- **You, on the Vectorworks Mac** — download the code, run the two checks in
  Vectorworks, and report what happened. **You don't need a GitHub account or
  any git setup — a ZIP download is enough.**

## Getting the code onto the Vectorworks Mac

The developer publishes the code to GitHub first. Then, on the Vectorworks Mac:

1. In a web browser, open the GitHub page for the code and switch to the branch
   you were asked to test.
2. Click the green **Code** button → **Download ZIP**.
3. Double-click the downloaded ZIP to unzip it, then open the Terminal app and
   `cd` into the unzipped folder. Everything runs from there, wherever you put
   it.

> One macOS quirk: unzipping removes the "runnable" flag from the helper script,
> so start it with `bash …` (as shown below) rather than double-clicking it.

Nothing needs installing — the checks use the Python that already comes with
macOS, and Vectorworks provides its own scripting for the rest.

(If you happen to have git set up, you can `git clone` the repository and
`git checkout` the branch instead — but the ZIP is the simplest path.)

## The two checks

These are quick, throwaway trials to confirm two things work on macOS +
Vectorworks 2026 before the real tool is built on top of them. Both are
pass/fail — and a clear **"no, this doesn't work"** is a genuinely useful
result, so don't worry if one fails. The trial code lives in
[`../spike/`](../spike/).

### Check A — the listener window doesn't freeze Vectorworks

Confirms a small window can sit open inside Vectorworks, quietly wait for a
request, and answer it (returning the open drawing's file name) **without
locking up Vectorworks while it's open**.

On the Vectorworks Mac:

1. Open Vectorworks 2026 with any drawing (a blank one is fine).
2. Load the helper script: **Resource Manager** (`Cmd+R`) → **New Resource** →
   **Script** → **Python** → paste in the entire contents of
   [`spike/vw_modal_listener.py`](../spike/vw_modal_listener.py) → **run**.
3. A small **"VW MCP Spike"** window opens and stays open.
4. **Check Vectorworks still responds**: with that window open, pan and zoom the
   drawing — it should move normally, not freeze.
5. In the Terminal app, run:
   ```
   python3 spike/poke.py
   ```
6. Click **Stop** (or close the window) when you're done — that hands
   Vectorworks back to you.

**Pass** if: the window opens, Vectorworks keeps responding while it's open, and
the Terminal prints `PASS: round trip OK. Open document filename = ...` showing
the real file name. **Fail** (still a useful result) if Vectorworks freezes or
no real file name comes back.

### Check B — install it once so it survives a restart

Confirms the helper can be added to a Vectorworks menu **once**, so that after
quitting and reopening Vectorworks it's still there and can be started from the
menu — with no pasting each time. (Behind the scenes the menu item just points
at the script file, so the script can be updated later without touching the
menu.)

On the Vectorworks Mac:

1. Open Vectorworks 2026 once (so it creates its settings folder).
2. In the Terminal app, run:
   ```
   bash spike/persistent_probe/install.sh
   ```
   This prepares the menu snippet, copies it to your clipboard, and confirms the
   folder Vectorworks uses for add-ons
   (`~/Library/Application Support/Vectorworks/2026/Plug-ins`).
3. Add the menu command **once**: **Tools → Plug-ins → Plug-in Manager → New →
   Menu Command**, paste the snippet (already on your clipboard), save, then add
   it to a menu via the Workspace editor. The Terminal prints the exact clicks.
4. **Quit Vectorworks and reopen it** — this is the real test.
5. Click the new **"VW MCP Spike"** menu command. The listener window should open
   with no pasting. Then run `python3 spike/poke.py` again to confirm it answers
   (same as Check A).

**Pass** if: after reopening Vectorworks the menu command is still there and
starts the listener with no pasting. **Fail** (still a useful result) if it's
gone after the restart, or the add-ons folder isn't where expected on
Vectorworks 2026.

## Reporting back

Send both results to the developer (recorded on the [LAB-9] issue):

- **Check A:** pass/fail — did Vectorworks keep responding? what file name came
  back?
- **Check B:** pass/fail — was the menu command still there after a restart and
  did it start without pasting? what was the actual add-ons folder path?

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold
[LAB-8]: https://linear.app/edmacovaz/issue/LAB-8/document-manifest-tool
