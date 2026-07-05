"""LAB-9 Probe B — stable loader for a persistent menu command (DISPOSABLE).

This is a *template*. ``install.sh`` installs the listener to a stable location
(outside the unzipped download, so deleting the download doesn't break this),
replaces the placeholder below with that path, and copies the result to your
clipboard so you can paste it *once* into a Vectorworks menu command.

Why a loader instead of pasting the listener directly (the prior-art lesson):
the menu command stores only these few lines; the real listener logic stays in
a file on disk. You can regenerate/edit the listener without ever touching the
menu command again. Clicking the menu command reads-and-runs the current
listener from disk — starting the modal session with no per-session paste.
"""

LISTENER_PATH = "__LISTENER_PATH__"

# encoding="utf-8" is required: VW 2026's embedded Python defaults to ASCII, so
# without it, reading the listener (which contains non-ASCII characters) raises
# UnicodeDecodeError.
with open(LISTENER_PATH, "r", encoding="utf-8") as _f:
    exec(compile(_f.read(), LISTENER_PATH, "exec"))
