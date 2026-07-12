"""Visual intermediate representation and the failure taxonomy.

Mirrors the data-model compiler's "no silent drops" discipline: a worksheet
that cannot be translated becomes a VisualNode with a ``skip_reason`` drawn from
:data:`SKIP_BUCKETS`, never a fabricated visual.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---- failure taxonomy buckets (report keys) ----
SKIP_BUCKETS = (
    "custom_geometry",       # generated-geometry / non-standard-region maps
    "map_choropleth",        # filled/choropleth-only map with no bubble equivalent
    "custom_shape",          # Shape design/KPI marks
    "gantt",                 # GanttBar
    "dual_axis",             # 2 measures stacked on one axis / multi-mark overlay
    "density",               # density / hexbin
    "unsupported_mark",      # mark type with no mapping
    "unmapped_encoding",     # a required field does not resolve to a model column
    "insufficient_fields",   # too few dims/measures for the target visual
    "unsupported_aggregation",  # Tableau aggregation with no verified DAX/PBI function
)

# Tableau aggregation prefix -> Power BI QueryAggregateFunction code.
# Only Sum (0) is reference-verified from pbir_reference; the rest come from the
# documented QueryAggregateFunction enum and are marked best-effort. Anything not
# in this map routes to the ``unsupported_aggregation`` skip bucket rather than
# being emitted with a guessed code.
AGG_FUNCTION = {
    "sum": 0,   # reference-verified (pbir_reference visual.json)
    "avg": 1,   # documented enum (best-effort)
    "min": 3,   # documented enum (best-effort)
    "max": 4,   # documented enum (best-effort)
    "cnt": 5,   # documented enum (best-effort)
}
AGG_DISPLAY = {"sum": "Sum", "avg": "Average", "min": "Min", "max": "Max", "cnt": "Count"}


@dataclass
class FieldRef:
    """A field bound in a visual. ``aggregation`` None => dimension."""
    entity: str
    column: str
    aggregation: str | None = None   # Tableau prefix: "sum"/"avg"/... or None

    @property
    def is_measure(self) -> bool:
        return self.aggregation is not None


@dataclass
class Position:
    x: float
    y: float
    z: int
    width: float
    height: float


@dataclass
class VisualNode:
    worksheet: str
    mark_type: str
    visual_type: str | None = None
    wells: dict[str, list[FieldRef]] = field(default_factory=dict)
    unmapped_encodings: list[dict] = field(default_factory=list)
    skip_reason: str | None = None
    position: Position | None = None

    @property
    def emitted(self) -> bool:
        return self.visual_type is not None and self.skip_reason is None


@dataclass
class PageNode:
    id: str
    name: str
    display_name: str
    visuals: list[VisualNode] = field(default_factory=list)
