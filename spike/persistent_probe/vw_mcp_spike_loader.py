"""LAB-9 Probe B — stable loader for a persistent menu command (DISPOSABLE).

This is a *template*. ``install.sh`` replaces the placeholder below with the
absolute path to ``spike/vw_modal_listener.py`` on this machine and copies the
result to your clipboard so you can paste it *once* into a Vectorworks menu
command.

Why a loader instead of pasting the listener directly (the prior-art lesson):
the menu command stores only these few lines; the real listener logic stays in
the repo on disk. You can regenerate/edit the listener without ever touching
the menu command again. Clicking the menu command reads-and-runs the current
listener from disk — starting the modal session with no per-session paste.
"""

LISTENER_PATH = "__LISTENER_PATH__"

with open(LISTENER_PATH, "r") as _f:
    exec(compile(_f.read(), LISTENER_PATH, "exec"))
