#!/usr/bin/env python3
"""Install the VW MCP scaffold on a macOS + Vectorworks 2026 machine.

Runs with the **system** ``python3`` (no ``uv``, no dev tooling — this is the
architect side, not the contributor side). Note a split interpreter requirement:
the in-VW *listener* runs in Vectorworks' embedded Python 3.9, but the host *MCP
server* runs on FastMCP, which needs **Python 3.10+**. macOS's system ``python3``
is often 3.9, so this script *discovers* a 3.10+ interpreter for the server's
venv and stops with a clear message if there isn't one. It automates everything
on disk and then hands you two short manual steps that can't be done from a
script:

  1. Copy the ``vw_mcp`` package + listener to a stable location that survives
     deleting the download (``~/Library/Application Support/vw-mcp``).
  2. Create an isolated venv there and ``pip install fastmcp`` for the host MCP
     server — isolated, so it touches no existing Python setup.
  3. Generate the **stable loader** (paths baked in) and copy it to the clipboard
     for a one-time paste into a Plug-in Manager Command.
  4. Confirm/create the VW 2026 user Plug-ins folder.
  5. Print the ready-to-use MCP server launch command for your client.

Deliberately NOT automated (see LAB-6 plan):
  * The one-time paste + Workspace-editor step (auto-registration is LAB-11).
  * Editing the MCP client's config — we print the command instead of writing
    ``~/.claude.json`` / ``.mcp.json``, to avoid coupling to the client's setup.

Usage:  python3 scripts/install.py [VW_VERSION]   (VW_VERSION defaults to 2026)
"""

import shutil
import subprocess
import sys
from pathlib import Path

VW_HOST = "127.0.0.1"
VW_PORT = 9877

# The one-time loader pasted into the Plug-in Manager Command. It puts the stable
# dir on sys.path (so `import vw_mcp` resolves) and reads-and-runs the listener
# from disk — so updating listener logic is a file swap + relaunch, never a
# re-paste. encoding="utf-8" is required: VW 2026's embedded Python defaults to
# ASCII and would raise UnicodeDecodeError on non-ASCII content otherwise.
_LOADER_TEMPLATE = """\
# VW MCP stable loader — paste this ONCE into a Plug-in Manager Command.
import sys

STABLE_DIR = "__STABLE_DIR__"
LISTENER_PATH = "__LISTENER_PATH__"

if STABLE_DIR not in sys.path:
    sys.path.insert(0, STABLE_DIR)

with open(LISTENER_PATH, "r", encoding="utf-8") as _f:
    exec(compile(_f.read(), LISTENER_PATH, "exec"))
"""


def _copy_package(repo_root: Path, stable_dir: Path) -> Path:
    """Copy the ``vw_mcp`` package into the stable dir; return the copy's path."""
    src = repo_root / "vw_mcp"
    dst = stable_dir / "vw_mcp"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def _is_310plus(python: str) -> bool:
    try:
        subprocess.check_call(
            [
                python,
                "-c",
                "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, OSError):
        return False


def _find_host_python() -> "str | None":
    """Find a Python 3.10+ interpreter for the host server's venv (FastMCP needs it).

    Prefers an explicit modern minor on PATH, then falls back to whatever
    ``python3`` / this script's own interpreter is — but only if new enough.
    """
    for name in ("python3.13", "python3.12", "python3.11", "python3.10"):
        path = shutil.which(name)
        if path and _is_310plus(path):
            return path
    for path in (sys.executable, shutil.which("python3")):
        if path and _is_310plus(path):
            return path
    return None


def _make_venv(stable_dir: Path, host_python: str) -> Path:
    """Create an isolated venv from ``host_python`` and install fastmcp into it."""
    venv_dir = stable_dir / "venv"
    print("Creating isolated venv at {} (from {}) ...".format(venv_dir, host_python))
    subprocess.check_call([host_python, "-m", "venv", str(venv_dir)])
    venv_python = venv_dir / "bin" / "python"
    print("Installing fastmcp into the venv (one-time, needs network) ...")
    subprocess.check_call(
        [str(venv_python), "-m", "pip", "install", "--quiet", "fastmcp>=3"]
    )
    return venv_python


def _write_loader(stable_dir: Path, listener_path: Path) -> Path:
    loader = _LOADER_TEMPLATE.replace("__STABLE_DIR__", str(stable_dir)).replace(
        "__LISTENER_PATH__", str(listener_path)
    )
    loader_path = stable_dir / "vw_mcp_loader.py"
    loader_path.write_text(loader, encoding="utf-8")
    if shutil.which("pbcopy"):
        subprocess.run(["pbcopy"], input=loader.encode("utf-8"), check=False)
        print("Loader copied to clipboard (pbcopy).")
    else:
        print(
            "pbcopy unavailable; copy the loader contents from {} manually.".format(
                loader_path
            )
        )
    return loader_path


def main() -> int:
    vw_version = sys.argv[1] if len(sys.argv) > 1 else "2026"
    repo_root = Path(__file__).resolve().parent.parent
    stable_dir = Path.home() / "Library" / "Application Support" / "vw-mcp"
    app_support_vw = (
        Path.home() / "Library" / "Application Support" / "Vectorworks" / vw_version
    )
    plugins_dir = app_support_vw / "Plug-ins"

    # An existing loader means this is an update, not a fresh install — the
    # architect must NOT paste or re-add the menu command again, so we tailor the
    # closing guidance below.
    updating = (stable_dir / "vw_mcp_loader.py").exists()

    stable_dir.mkdir(parents=True, exist_ok=True)

    verb = "Updating" if updating else "Installing"
    print(
        "{} vw_mcp at a stable location (survives deleting the download):".format(verb)
    )
    _copy_package(repo_root, stable_dir)
    listener_path = stable_dir / "vw_mcp" / "listener.py"
    print("  {}".format(stable_dir / "vw_mcp"))

    host_python = _find_host_python()
    venv_python = None
    if host_python is None:
        print()
        print(
            "WARNING: no Python 3.10+ found — the host MCP server (FastMCP) needs one."
        )
        print("  The listener runs in VW's embedded 3.9, but the server does not.")
        print("  Install Python 3.10+ (e.g. `brew install python@3.12` or python.org),")
        print("  then re-run this script to finish the server's venv.")
    else:
        try:
            venv_python = _make_venv(stable_dir, host_python)
        except subprocess.CalledProcessError as exc:
            print(
                "WARNING: could not build the server venv ({}). Re-run after fixing.".format(
                    exc
                )
            )

    loader_path = _write_loader(stable_dir, listener_path)
    print(
        "Generated stable loader:\n  {}\n  -> runs: {}\n".format(
            loader_path, listener_path
        )
    )

    print("Checking macOS VW {} user Plug-ins path...".format(vw_version))
    if app_support_vw.is_dir():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        print("  Plug-ins folder: {}".format(plugins_dir))
    else:
        print("  NOT FOUND: {}".format(app_support_vw))
        print(
            "  Open Vectorworks {} at least once so it creates this folder,".format(
                vw_version
            )
        )
        print("  then re-run this script.")
    print()

    server_python = (
        venv_python
        if venv_python is not None
        else (stable_dir / "venv" / "bin" / "python")
    )
    print("=" * 72)
    print("Connect Claude to the MCP server (a one-time step).")
    print("Run the command below in the Terminal, or pass it to your developer to")
    print("set up. If you are updating an existing install, this is unchanged.")
    if venv_python is None:
        print("(The venv isn't built yet — finish the Python 3.10+ step above first.)")
    print("The server settings are:")
    print("  command: {}".format(server_python))
    print('  args:    ["-m", "vw_mcp.server"]')
    print(
        '  env:     {{"PYTHONPATH": "{}", "VW_MCP_HOST": "{}", "VW_MCP_PORT": "{}"}}'.format(
            stable_dir, VW_HOST, VW_PORT
        )
    )
    print()
    print("For Claude Code that is, in one line:")
    print(
        '  claude mcp add-json vw-mcp \'{{"command": "{}", "args": ["-m", "vw_mcp.server"], '
        '"env": {{"PYTHONPATH": "{}"}}}}\''.format(server_python, stable_dir)
    )
    print("=" * 72)
    print()

    if updating:
        print("This refreshed an existing install — the menu command and the Claude")
        print("connection are unchanged, so there's nothing to paste or set up again.")
        print("To load the new version:")
        print("  1. If a VW MCP Session window is open, close it and open it again")
        print("     from the menu (it re-reads the updated tool).")
        print("  2. If the update also changed the server, restart Claude.")
    else:
        print("Finish the setup in Vectorworks (a one-time step):")
        print("  1. Tools > Plug-ins > Plug-in Manager > New > Command (NOT Tool).")
        print('     Name it "VW MCP Session".')
        print(
            "  2. Edit its script, PASTE the loader (already on your clipboard), and save."
        )
        print(
            "  3. Tools > Workspaces > Edit Current Workspace > Menus: drag it into a menu."
        )
        print("  4. Open a drawing, click VW MCP Session, then ask Claude to check the")
        print("     connection to Vectorworks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
