#!/usr/bin/env bash
# LAB-9 Probe B — persistent, no-paste install helper (DISPOSABLE).
#
# Installs the listener to a stable location, prepares the "stable loader" you
# paste ONCE into a Vectorworks menu command, and reports whether the macOS VW
# 2026 user Plug-ins path exists. It does NOT create the menu command for you —
# that is a one-time Vectorworks UI action (Plug-in Manager + Workspace editor)
# documented in the README. The point of this probe is the go/no-go: after that
# one-time setup, does the menu command survive a relaunch and start the session
# with no per-session paste?
#
# Usage:  ./install.sh [VW_VERSION]     (VW_VERSION defaults to 2026)

set -euo pipefail

VW_VERSION="${1:-2026}"

# Resolve paths relative to this script so it works from any checkout location.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LISTENER_PATH="$REPO_ROOT/spike/vw_modal_listener.py"
TEMPLATE="$SCRIPT_DIR/vw_mcp_spike_loader.py"
GENERATED_DIR="$SCRIPT_DIR/generated"
GENERATED="$GENERATED_DIR/vw_mcp_spike_loader.py"

# The menu command must survive the download being moved or deleted, so we copy
# the listener to a stable location OUTSIDE the unzipped folder and point the
# menu command there. (This folder is not scanned by Vectorworks, so the copy
# won't auto-run on launch.)
STABLE_DIR="$HOME/Library/Application Support/vw-mcp-spike"
STABLE_LISTENER="$STABLE_DIR/vw_modal_listener.py"

PLUGINS_DIR="$HOME/Library/Application Support/Vectorworks/$VW_VERSION/Plug-ins"
VW_USER_DIR="$HOME/Library/Application Support/Vectorworks/$VW_VERSION"

if [ ! -f "$LISTENER_PATH" ]; then
  echo "ERROR: listener not found at $LISTENER_PATH" >&2
  exit 1
fi

# Copy the listener to the stable location, then bake THAT path into the loader.
mkdir -p "$STABLE_DIR"
cp "$LISTENER_PATH" "$STABLE_LISTENER"
mkdir -p "$GENERATED_DIR"
sed "s|__LISTENER_PATH__|$STABLE_LISTENER|g" "$TEMPLATE" >"$GENERATED"

echo "Installed listener (survives deleting the download):"
echo "  $STABLE_LISTENER"
echo "Generated stable loader:"
echo "  $GENERATED"
echo "  -> runs: $STABLE_LISTENER"
echo

# Feasibility signal: does the macOS VW 2026 user folder / Plug-ins path exist?
echo "Checking macOS VW $VW_VERSION user Plug-ins path..."
if [ -d "$VW_USER_DIR" ]; then
  echo "  FOUND VW user folder: $VW_USER_DIR"
  if [ -d "$PLUGINS_DIR" ]; then
    echo "  FOUND Plug-ins folder: $PLUGINS_DIR"
  else
    echo "  Plug-ins subfolder missing; creating it: $PLUGINS_DIR"
    mkdir -p "$PLUGINS_DIR"
  fi
else
  echo "  NOT FOUND: $VW_USER_DIR"
  echo "  Open Vectorworks $VW_VERSION at least once so it creates this folder,"
  echo "  then re-run this script. (Confirming this path is part of the probe.)"
fi
echo

# Copy the loader to the clipboard for the one-time paste into the menu command.
if command -v pbcopy >/dev/null 2>&1; then
  pbcopy <"$GENERATED"
  echo "Loader copied to clipboard (pbcopy)."
else
  echo "pbcopy unavailable; copy the loader contents from $GENERATED manually."
fi

cat <<EOF

Next (one-time setup, then it persists across relaunches):
  1. Vectorworks: Tools > Plug-ins > Plug-in Manager > New > Menu Command.
     Name it "VW MCP Spike".
  2. Edit its script and PASTE the loader (already on your clipboard). Save.
  3. Tools > Workspaces > Edit Current Workspace > Menus: drag "VW MCP Spike"
     into a menu. Save the workspace.
  4. QUIT and reopen Vectorworks $VW_VERSION  <-- this is the persistence test.
  5. Click the "VW MCP Spike" menu command. The modal session should open with
     NO pasting. Then run:  python3 spike/poke.py

PASS if the menu command is still present after the relaunch and starts the
session with no paste. FAIL (a valid result) if it does not survive relaunch or
the folder path differs on VW $VW_VERSION — record either outcome on LAB-9.
EOF
