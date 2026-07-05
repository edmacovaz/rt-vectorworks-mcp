# LAB-9 spike (DISPOSABLE)

Throwaway feasibility probes for [LAB-9]. Not production code — [LAB-6] deletes
this directory once the findings land. The durable output is
[`../docs/test-handoff-workflow.md`](../docs/test-handoff-workflow.md), which
has the full run procedure and pass/fail criteria.

- `vw_modal_listener.py` — **Probe A**: minimal modal-dialog session that pumps a
  `127.0.0.1:9877` loopback socket and answers one read-only `vs.*` call
  (`vs.GetFName()`). Paste into a VW Python script and run.
- `poke.py` — Probe A client: pokes the listener and prints the filename.
- `persistent_probe/` — **Probe B**: `install.sh` + a stable-loader template to
  prove a persistent, no-paste menu command on macOS/VW 2026.

Everything is stdlib-only; the `vs` module is supplied by Vectorworks.

[LAB-9]: https://linear.app/edmacovaz/issue/LAB-9/repeatable-vw-test-handoff-workflow
[LAB-6]: https://linear.app/edmacovaz/issue/LAB-6/mcp-round-trip-scaffold
