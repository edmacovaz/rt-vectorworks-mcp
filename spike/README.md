# Test instructions — first implementation (LAB-9)

> **Throwaway trial code.** These are the step-by-step checks for the POC's
> first implementation. The code here is disposable — it will be removed once
> the real scaffold lands ([LAB-6]). The durable part is the handoff process in
> the [top-level README](../README.md).

First get the code onto a Mac with **Vectorworks 2026** and open a Terminal in
the unzipped folder — see [**Running it on a Vectorworks
Mac**](../README.md#running-it-on-a-vectorworks-mac) in the top-level README.

There are **two checks**. Both are pass/fail — and a clear **"no, this doesn't
work"** is a genuinely useful answer, so don't worry if one fails. Report both
results back to the developer.

---

## Check A — the listener window doesn't freeze Vectorworks

Confirms a small window can sit open inside Vectorworks, quietly wait for a
request, and answer it (returning the open drawing's file name) **without
locking up Vectorworks while it's open**.

1. Open Vectorworks 2026 with any drawing (a blank one is fine).
2. Load the helper script: **Resource Manager** (`Cmd+R`) → **New Resource** →
   **Script** → **Python** → paste in the entire contents of
   [`vw_modal_listener.py`](vw_modal_listener.py) → **run**.
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
the real file name.
**Fail** (still a useful result) if Vectorworks freezes or no real file name
comes back.

---

## Check B — install it once so it survives a restart

Confirms the helper can be added to a Vectorworks menu **once**, so that after
quitting and reopening Vectorworks it's still there and can be started from the
menu — with no pasting each time. (Behind the scenes the menu item just points
at the script file, so the script can be updated later without touching the
menu.)

1. Open Vectorworks 2026 once (so it creates its settings folder).
2. In the Terminal app, run:
   ```
   bash spike/persistent_probe/install.sh
   ```
   This installs the listener to a stable spot, prepares the menu snippet, copies
   it to your clipboard, and confirms the folder Vectorworks uses for add-ons
   (`~/Library/Application Support/Vectorworks/2026/Plug-ins`). Because the
   listener is copied out of the download, you can delete the unzipped folder
   afterwards and the menu command still works.
3. Add the menu command **once**: **Tools → Plug-ins → Plug-in Manager → New →
   Menu Command**, paste the snippet (already on your clipboard), save, then add
   it to a menu via the Workspace editor. The Terminal prints the exact clicks.
4. **Quit Vectorworks and reopen it** — this is the real test.
5. Click the new **"VW MCP Spike"** menu command. The listener window should open
   with no pasting. Then run `python3 spike/poke.py` again to confirm it answers
   (same as Check A).

**Pass** if: after reopening Vectorworks the menu command is still there and
starts the listener with no pasting.
**Fail** (still a useful result) if it's gone after the restart, or the add-ons
folder isn't where expected on Vectorworks 2026.

---

## What's in this folder

- `vw_modal_listener.py` — Check A: the small listener window that answers one
  read-only request (`vs.GetFName()`, the open drawing's file name).
- `poke.py` — sends the request and prints the answer.
- `persistent_probe/` — Check B: `install.sh` plus the menu snippet it prepares.

All of it is plain Python; Vectorworks supplies the `vs` scripting module.

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold
