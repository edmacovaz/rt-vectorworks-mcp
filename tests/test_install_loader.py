"""The generated stable loader actually reads-and-runs the listener (no VW).

Guards the mechanism the installed Plug-in Manager Command relies on — repr-baked
paths, exec in a fresh namespace, and the explicit ``run()`` call — which is
otherwise only exercised live at the VW handoff. The listener module itself has
no import-time side effect; the loader is what starts the session.
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_install_module():
    spec = importlib.util.spec_from_file_location(
        "vw_install", REPO_ROOT / "scripts" / "install.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generated_loader_execs_listener_and_calls_run(tmp_path):
    install = _load_install_module()
    # A stable dir whose name contains a space, to prove repr() path escaping.
    stable_dir = tmp_path / "vw mcp"
    stable_dir.mkdir()
    marker = tmp_path / "ran.txt"
    listener = stable_dir / "listener.py"
    listener.write_text(
        "def run():\n    open({!r}, 'w').write('ran')\n".format(str(marker)),
        encoding="utf-8",
    )

    loader_path = install._write_loader(stable_dir, listener)
    exec(compile(loader_path.read_text(encoding="utf-8"), str(loader_path), "exec"), {})

    assert marker.read_text(encoding="utf-8") == "ran"


def test_importing_the_listener_has_no_side_effect():
    # Off-VW `vs` is None so run() couldn't proceed anyway, but the contract is
    # that importing the module never even attempts to start a session.
    import vw_mcp.listener as listener

    assert hasattr(listener, "run")
    assert hasattr(listener, "SocketPump")
