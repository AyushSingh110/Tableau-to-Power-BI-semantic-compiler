"""Deterministic mark -> visual mapping.

One table drives translation. Anything the table cannot satisfy returns a
``skip_reason`` from :data:`~tab2pbi.visual.ir.SKIP_BUCKETS` — never a guessed or
plausible-but-wrong visual.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ir import FieldRef

# Geographic columns Power BI/Bing geocodes as standard admin regions.
GEO_STANDARD = {
    "state", "city", "country", "country/region", "postal code",
    "county", "zip code", "province", "state/province",
}


@dataclass
class Plan:
    """Result of classify(): either a visual plan or a skip reason."""
    visual_type: str | None = None
    wells: dict | None = None
    skip_reason: str | None = None


def _measure_wells(dims, measures, roles):
    """Assign dims/measures to the given (dim_role, measure_role) names."""
    dim_role, meas_role = roles
    wells: dict[str, list[FieldRef]] = {}
    if dim_role and dims:
        wells[dim_role] = [dims[0]]
        if len(dims) > 1:
            wells.setdefault("Series", []).append(dims[1])
    wells[meas_role] = [measures[0]]
    return wells


def classify(
    mark_type: str,
    dims: list[FieldRef],
    measures: list[FieldRef],
    *,
    geo_standard_dim: FieldRef | None = None,
    generated_geometry: bool = False,
    multi_mark: bool = False,
) -> Plan:
    """Map one worksheet's mark + fields to a PBIR visual, or a skip reason."""

    # --- hard skips first (never emit) ---
    if mark_type == "GanttBar":
        return Plan(skip_reason="gantt")
    if mark_type == "Shape":
        return Plan(skip_reason="custom_shape")
    if multi_mark:
        return Plan(skip_reason="dual_axis")

    # --- geographic (bubble map approximation) ---
    # A map is intended when the mark is a map, a location is geocodable, or the
    # sheet carries generated geometry (Tableau's auto lat/long). Generated
    # geometry alone is NOT a skip — only a *non-standard* location is (custom
    # territory polygons that Bing/Azure can't geocode).
    if mark_type in ("Multipolygon", "Map") or generated_geometry or geo_standard_dim is not None:
        if geo_standard_dim is None:
            return Plan(skip_reason="custom_geometry")
        if not measures:
            return Plan(skip_reason="insufficient_fields")
        return Plan(
            visual_type="map",
            wells={"Category": [geo_standard_dim], "Size": [measures[0]]},
        )

    # --- cartesian / text ---
    if mark_type in ("Bar", "Automatic"):
        if not dims or not measures:
            return Plan(skip_reason="insufficient_fields")
        return Plan(visual_type="columnChart", wells=_measure_wells(dims, measures, ("Category", "Y")))

    if mark_type == "Line":
        if not dims or not measures:
            return Plan(skip_reason="insufficient_fields")
        return Plan(visual_type="lineChart", wells=_measure_wells(dims, measures, ("Category", "Y")))

    if mark_type == "Area":
        if not dims or not measures:
            return Plan(skip_reason="insufficient_fields")
        return Plan(visual_type="areaChart", wells=_measure_wells(dims, measures, ("Category", "Y")))

    if mark_type == "Pie":
        if not dims or not measures:
            return Plan(skip_reason="insufficient_fields")
        return Plan(visual_type="pieChart", wells=_measure_wells(dims, measures, ("Category", "Y")))

    if mark_type == "Circle":
        # scatter needs TWO measures (X and Y); one measure alone is not a scatter.
        if len(measures) < 2:
            return Plan(skip_reason="insufficient_fields")
        wells = {"X": [measures[0]], "Y": [measures[1]]}
        if dims:
            wells["Details"] = [dims[0]]
        return Plan(visual_type="scatterChart", wells=wells)

    if mark_type == "Text":
        if measures and not dims:
            return Plan(visual_type="card", wells={"Values": [measures[0]]})
        if dims and measures:
            return Plan(visual_type="tableEx", wells={"Values": dims + measures})
        # Dims-only text with several columns is a detail table. A single dim
        # is usually a KPI whose value is an (unconverted) calc — keep skipping
        # that, since a 1-column table would misrepresent it.
        if len(dims) >= 2 and not measures:
            return Plan(visual_type="tableEx", wells={"Values": dims})
        return Plan(skip_reason="insufficient_fields")

    return Plan(skip_reason="unsupported_mark")
