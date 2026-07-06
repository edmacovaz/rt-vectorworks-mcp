"""The `vs` seam — the single boundary between companion logic and Vectorworks.

`vs.*` only exists inside Vectorworks' embedded Python interpreter, so importing
it anywhere else fails. To keep the companion logic pure and checkable with
Vectorworks closed, *all* companion code is typed against the ``VsPort`` protocol
and never touches ``vs`` directly. This module is the one place ``import vs``
happens; off-Vectorworks, ``StubVsAdapter`` stands in.

Keep this surface narrow: add a method only when a tool genuinely needs a new
``vs.*`` call, and keep each method a thin, read-only pass-through.
"""

from __future__ import annotations

from typing import Protocol


class VsPort(Protocol):
    """The narrow slice of the Vectorworks ``vs.*`` API the companion depends on.

    Companion logic is typed against this protocol, never the real ``vs`` module,
    which is what lets it be exercised off-Vectorworks with a stub.
    """

    def get_open_filename(self) -> str:
        """Filename of the currently open document (``"Untitled"`` if unsaved)."""
        ...


class VectorworksAdapter:
    """Live adapter backed by Vectorworks' embedded ``vs`` module.

    The *only* place ``import vs`` happens. Constructing it outside Vectorworks
    raises by design — off-VW code uses :class:`StubVsAdapter` instead.
    """

    def __init__(self) -> None:
        try:
            import vs
        except ImportError as exc:  # pragma: no cover - only reachable inside VW
            raise RuntimeError(
                "VectorworksAdapter requires Vectorworks' embedded Python; the "
                "`vs` module is unavailable here. Use StubVsAdapter off-VW."
            ) from exc
        self._vs = vs

    def get_open_filename(self) -> str:
        # GetFName returns "" for an unsaved document; normalise to "Untitled".
        return self._vs.GetFName() or "Untitled"


class StubVsAdapter:
    """In-memory stand-in for the no-Vectorworks tests and local runs."""

    def __init__(self, filename: str = "Untitled") -> None:
        self._filename = filename

    def get_open_filename(self) -> str:
        return self._filename
