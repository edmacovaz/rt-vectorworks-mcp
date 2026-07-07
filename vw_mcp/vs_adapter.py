"""The `vs` seam — the single boundary between companion logic and Vectorworks.

`vs.*` only exists inside Vectorworks' embedded Python interpreter, so importing
it anywhere else fails. To keep the companion logic pure and checkable with
Vectorworks closed, *all* companion code is typed against the ``VsPort`` protocol
and never touches ``vs`` directly. This module is the one place ``import vs``
happens; off-Vectorworks, ``StubVsAdapter`` stands in.

Keep this surface narrow: add a method only when a tool genuinely needs a new
``vs.*`` call, and keep each method a thin, read-only pass-through. The shape
logic that *assembles* these reads into a tool response lives in
:mod:`vw_mcp.dispatch`, so it stays pure and testable — the adapter only reads.

Runs inside VW 2026's embedded Python 3.9, so keep it 3.9-compatible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Set, Tuple

# An RGB colour as three 0–255 channels (Vectorworks returns longints per channel).
Rgb = Tuple[int, int, int]

# A resource-backed fill captured *by reference*: its kind ("hatch", "gradient",
# "tile", "image") and the resource's name — not the resource's internals. See
# dispatch/read_classes for why identity-by-name is enough for template work.
FillResource = Tuple[str, str]


class VsPort(Protocol):
    """The narrow slice of the Vectorworks ``vs.*`` API the companion depends on.

    Companion logic is typed against this protocol, never the real ``vs`` module,
    which is what lets it be exercised off-Vectorworks with a stub. Every method
    is a read; nothing here mutates the document.
    """

    def get_open_filename(self) -> str:
        """Filename of the currently open document (``"Untitled"`` if unsaved)."""
        ...

    # --- Class enumeration -------------------------------------------------
    def class_count(self) -> int:
        """Number of classes in the document (``vs.ClassNum()``)."""
        ...

    def class_name_at(self, index: int) -> str:
        """Name of the ``index``-th class, **1-based** (``vs.ClassList(i)``)."""
        ...

    # --- Per-class attributes (all keyed by class name) --------------------
    def class_pen_fore(self, name: str) -> Rgb:
        """Foreground pen colour."""
        ...

    def class_pen_back(self, name: str) -> Rgb:
        """Background pen colour."""
        ...

    def class_line_weight(self, name: str) -> int:
        """Line weight (Vectorworks mils)."""
        ...

    def class_line_style(self, name: str) -> int:
        """Line style index (0 = solid; other values index a line-type resource)."""
        ...

    def class_fill_fore(self, name: str) -> Rgb:
        """Foreground fill colour."""
        ...

    def class_fill_back(self, name: str) -> Rgb:
        """Background fill colour."""
        ...

    def class_fill_pattern(self, name: str) -> int:
        """Fill pattern index."""
        ...

    def class_fill_resource(self, name: str) -> Optional[FillResource]:
        """The class's resource-backed fill by reference, or ``None`` for a
        plain pattern/solid fill (see :data:`FillResource`)."""
        ...

    def class_opacity(self, name: str) -> int:
        """Opacity percentage (0–100)."""
        ...

    def class_visible(self, name: str) -> bool:
        """Whether the class is visible (vs. hidden/greyed)."""
        ...

    def class_uses_graphics(self, name: str) -> bool:
        """Whether the class applies its own graphic attributes at creation."""
        ...

    # --- Usage -------------------------------------------------------------
    def classes_in_use(self) -> Set[str]:
        """Names of classes with at least one object assigned, found in a single
        document traversal (see dispatch/read_classes for why a boolean, not a
        count)."""
        ...


class VectorworksAdapter:
    """Live adapter backed by Vectorworks' embedded ``vs`` module.

    The *only* place ``import vs`` happens. Constructing it outside Vectorworks
    raises by design — off-VW code uses :class:`StubVsAdapter` instead.

    The exact ``vs.*`` class-attribute calls below are the POC's best reading of
    the VW 2026 developer reference; because this class can only run *inside*
    Vectorworks it is never exercised by the no-VW net, so the names and return
    shapes are **proven at the LAB-8 live E2E handoff**, not here (see AGENTS.md).
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

    def class_count(self) -> int:
        return self._vs.ClassNum()

    def class_name_at(self, index: int) -> str:
        return self._vs.ClassList(index)

    def class_pen_fore(self, name: str) -> Rgb:
        return self._vs.GetClPenFore(name)

    def class_pen_back(self, name: str) -> Rgb:
        return self._vs.GetClPenBack(name)

    def class_line_weight(self, name: str) -> int:
        return self._vs.GetClLW(name)

    def class_line_style(self, name: str) -> int:
        return self._vs.GetClLS(name)

    def class_fill_fore(self, name: str) -> Rgb:
        return self._vs.GetClFillFore(name)

    def class_fill_back(self, name: str) -> Rgb:
        return self._vs.GetClFillBack(name)

    def class_fill_pattern(self, name: str) -> int:
        return self._vs.GetClFPat(name)

    def class_fill_resource(self, name: str) -> Optional[FillResource]:
        # A plain solid/pattern fill has no backing resource. When the fill is a
        # vector resource (hatch/gradient/tile/image) VW exposes it as a named
        # resource; capture (kind, name) by reference only. The precise call to
        # resolve kind+name is one of the E2E-verified points — until proven,
        # return None so a plain fill is the safe default.
        return None

    def class_opacity(self, name: str) -> int:
        return self._vs.GetClOpacity(name)

    def class_visible(self, name: str) -> bool:
        # GetClVis: 0 = visible, non-zero = hidden/greyed.
        return self._vs.GetClVis(name) == 0

    def class_uses_graphics(self, name: str) -> bool:
        return bool(self._vs.GetClUseGraphic(name))

    def classes_in_use(self) -> Set[str]:
        used: Set[str] = set()

        def collect(handle: object) -> None:
            used.add(self._vs.GetClass(handle))

        # One traversal of every object; tally the class each is assigned to.
        self._vs.ForEachObject(collect, "ALL")
        return used


@dataclass
class _StubClass:
    """One class in :class:`StubVsAdapter`'s in-memory document model.

    A plain record; every default is immutable (tuples/scalars/None), so no
    ``field(default_factory=...)`` is needed.
    """

    name: str
    in_use: bool = False
    pen_fore: Rgb = (0, 0, 0)
    pen_back: Rgb = (255, 255, 255)
    line_weight: int = 10
    line_style: int = 0
    fill_fore: Rgb = (255, 255, 255)
    fill_back: Rgb = (255, 255, 255)
    fill_pattern: int = 1
    fill_resource: Optional[FillResource] = None
    opacity: int = 100
    visible: bool = True
    uses_graphics: bool = True


class StubVsAdapter:
    """In-memory stand-in for the no-Vectorworks tests and local runs.

    Backed by an ordered list of :class:`_StubClass` records so a fixture can
    drive the whole ``read_classes`` shape with Vectorworks closed. With no
    classes supplied it behaves exactly as before (just a filename), keeping the
    existing ping/filename tests untouched.
    """

    def __init__(
        self,
        filename: str = "Untitled",
        classes: Optional[List[_StubClass]] = None,
    ) -> None:
        self._filename = filename
        self._classes = list(classes) if classes is not None else []

    def get_open_filename(self) -> str:
        return self._filename

    def class_count(self) -> int:
        return len(self._classes)

    def class_name_at(self, index: int) -> str:
        return self._classes[index - 1].name

    def _class(self, name: str) -> _StubClass:
        for cls in self._classes:
            if cls.name == name:
                return cls
        raise KeyError("no such class in stub: {!r}".format(name))

    def class_pen_fore(self, name: str) -> Rgb:
        return self._class(name).pen_fore

    def class_pen_back(self, name: str) -> Rgb:
        return self._class(name).pen_back

    def class_line_weight(self, name: str) -> int:
        return self._class(name).line_weight

    def class_line_style(self, name: str) -> int:
        return self._class(name).line_style

    def class_fill_fore(self, name: str) -> Rgb:
        return self._class(name).fill_fore

    def class_fill_back(self, name: str) -> Rgb:
        return self._class(name).fill_back

    def class_fill_pattern(self, name: str) -> int:
        return self._class(name).fill_pattern

    def class_fill_resource(self, name: str) -> Optional[FillResource]:
        return self._class(name).fill_resource

    def class_opacity(self, name: str) -> int:
        return self._class(name).opacity

    def class_visible(self, name: str) -> bool:
        return self._class(name).visible

    def class_uses_graphics(self, name: str) -> bool:
        return self._class(name).uses_graphics

    def classes_in_use(self) -> Set[str]:
        return {cls.name for cls in self._classes if cls.in_use}
