"""Extract Tableau worksheets/dashboards into the Visual IR.

Reuses the shipped field-name normalization (``ir.context.normalize_field_name``)
and resolves each Tableau field reference to a *real* column of the target model
(handling spaces/slashes/hyphens, e.g. ``Sub-Category``, ``Country/Region``,
``Order Date``). A reference that does not match a real model column is recorded
as an ``unmapped_encoding`` — never bound to a guessed Property.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..ir.context import normalize_field_name
from ..logging_config import get_logger
from . import mapping
from .ir import (
    AGG_FUNCTION,
    FieldRef,
    PageNode,
    Position,
    VisualNode,
)

log = get_logger(__name__)

# Tableau aggregation prefixes that denote a measure.
_AGG_PREFIXES = {"sum", "avg", "min", "max", "cnt", "cntd", "median", "stdev", "var", "attr"}
# Temporal truncation/part prefixes -> treated as (date) dimensions.
_TEMPORAL_PREFIXES = {"tyr", "tqr", "tmn", "tdy", "twk", "thr", "tmi", "tse", "ty", "tm", "td"}

_REF_RE = re.compile(r"\[[^\]]+\]\.\[[^\]]+\]")
_REF_PARTS_RE = re.compile(r"^\[(?P<ds>[^\]]*)\]\.\[(?P<inner>[^\]]*)\]$")

# Primary-mark priority (first present wins).
_MARK_PRIORITY = ["Multipolygon", "GanttBar", "Pie", "Bar", "Line", "Area", "Circle", "Shape", "Text", "Automatic"]
# Two distinct marks from this set on one sheet => classic dual axis.
_CARTESIAN_DUAL = {"Bar", "Line", "Area"}


def parse_encoded_ref(ref: str) -> tuple[str | None, str, str | None]:
    """Return (agg_prefix, field_name, role_flag) from a Tableau field ref."""
    m = _REF_PARTS_RE.match(ref.strip())
    inner = m.group("inner") if m else ref.strip().strip("[]")
    parts = inner.split(":")
    if len(parts) >= 3 and re.fullmatch(r"[a-z]{2,3}", parts[-1]):
        return parts[0], ":".join(parts[1:-1]), parts[-1]
    return None, inner.lstrip(":"), None


def _to_fieldref(ref: str, entity: str, columns_lc: dict[str, str]) -> tuple[FieldRef | None, dict | None]:
    """Resolve one ref to a FieldRef, or return (None, unmapped-record)."""
    prefix, name, _flag = parse_encoded_ref(ref)
    norm = normalize_field_name(name)
    if not norm or norm not in columns_lc:
        return None, {"field": name, "reason": "no matching model column"}
    real_col = columns_lc[norm]  # preserve exact model casing/spacing
    if prefix in _AGG_PREFIXES:
        return FieldRef(entity=entity, column=real_col, aggregation=prefix), None
    # 'none', temporal, or bare -> dimension
    return FieldRef(entity=entity, column=real_col, aggregation=None), None


def _refs_in(text: str | None) -> list[str]:
    return _REF_RE.findall(text) if text else []


def _analyze_worksheet(ws: ET.Element, entity: str, columns_lc: dict[str, str]) -> VisualNode:
    name = ws.attrib.get("name", "?")
    marks = [m.attrib.get("class") for m in ws.findall(".//pane/mark") if m.attrib.get("class")]
    mark_type = next((m for m in _MARK_PRIORITY if m in marks), (marks[0] if marks else "Automatic"))
    multi_mark = len({m for m in marks if m in _CARTESIAN_DUAL}) >= 2

    rows = ws.find(".//table/rows")
    cols = ws.find(".//table/cols")
    axis_refs = _refs_in(rows.text if rows is not None else None) + _refs_in(cols.text if cols is not None else None)

    encodings = [(e.tag, e.attrib.get("column", "")) for e in ws.findall(".//pane/encodings/*")]

    node = VisualNode(worksheet=name, mark_type=mark_type)

    dims: list[FieldRef] = []
    measures: list[FieldRef] = []
    for ref in axis_refs:
        fr, bad = _to_fieldref(ref, entity, columns_lc)
        if bad:
            node.unmapped_encodings.append({"shelf": "axis", **bad})
        elif fr.is_measure:
            measures.append(fr)
        else:
            dims.append(fr)

    # Geographic detection from encodings (lod/geometry) and axis dims.
    generated_geometry = any(
        tag == "geometry" and "generated" in (col or "").lower() for tag, col in encodings
    )
    geo_standard_dim = None
    geo_measure = None
    for tag, col in encodings:
        prefix, gname, _ = parse_encoded_ref(col)
        norm = normalize_field_name(gname)
        if tag in ("lod", "detail") and norm in mapping.GEO_STANDARD and norm in columns_lc:
            geo_standard_dim = FieldRef(entity=entity, column=columns_lc[norm], aggregation=None)
        if tag in ("color", "size") and prefix in _AGG_PREFIXES and norm in columns_lc:
            geo_measure = FieldRef(entity=entity, column=columns_lc[norm], aggregation=prefix)
    for d in dims:
        if normalize_field_name(d.column) in mapping.GEO_STANDARD:
            geo_standard_dim = geo_standard_dim or d
    if geo_measure and not measures:
        measures = [geo_measure]

    plan = mapping.classify(
        mark_type, dims, measures,
        geo_standard_dim=geo_standard_dim,
        generated_geometry=generated_geometry,
        multi_mark=multi_mark,
    )
    if plan.skip_reason:
        node.skip_reason = plan.skip_reason
        return node

    # Reject unsupported aggregations rather than emit a guessed Function code.
    for wells in plan.wells.values():
        for fr in wells:
            if fr.is_measure and fr.aggregation not in AGG_FUNCTION:
                node.skip_reason = "unsupported_aggregation"
                return node

    node.visual_type = plan.visual_type
    node.wells = plan.wells
    return node


def _dashboards(root: ET.Element) -> dict[str, list[str]]:
    """dashboard display name -> list of worksheet names it references."""
    out: dict[str, list[str]] = {}
    for dash in root.findall(".//dashboard"):
        dname = dash.attrib.get("name", "Dashboard")
        sheets = []
        for zone in dash.findall(".//zone"):
            wn = zone.attrib.get("name")
            if wn:
                sheets.append(wn)
        out[dname] = sheets
    return out


def _grid_positions(n: int, cols: int = 3, page_w: float = 1280, page_h: float = 720) -> list[Position]:
    """Deterministic auto-grid layout (dashboard positions are a V2 item)."""
    margin, gap = 16.0, 12.0
    rows = max(1, (n + cols - 1) // cols)
    cw = (page_w - 2 * margin - (cols - 1) * gap) / cols
    ch = (page_h - 2 * margin - (rows - 1) * gap) / max(rows, 1)
    positions = []
    for i in range(n):
        r, c = divmod(i, cols)
        positions.append(Position(
            x=round(margin + c * (cw + gap), 2),
            y=round(margin + r * (ch + gap), 2),
            z=i, width=round(cw, 2), height=round(ch, 2),
        ))
    return positions


def extract(twb_root: ET.Element, entity: str, columns: list[str]) -> list[PageNode]:
    """Build PageNodes (one per dashboard; loose worksheets -> default page)."""
    columns_lc = {normalize_field_name(c): c for c in columns}
    ws_by_name = {ws.attrib.get("name"): ws for ws in twb_root.findall(".//worksheet")}
    nodes = {name: _analyze_worksheet(ws, entity, columns_lc) for name, ws in ws_by_name.items()}

    dashboards = _dashboards(twb_root)
    used = set()
    pages: list[PageNode] = []
    for dname, sheets in dashboards.items():
        vis = [nodes[s] for s in sheets if s in nodes]
        if not vis:
            continue
        used.update(sheets)
        pages.append(PageNode(id="", name=dname, display_name=dname, visuals=vis))

    loose = [nodes[n] for n in ws_by_name if n not in used]
    if loose:
        pages.append(PageNode(id="", name="Worksheets", display_name="Worksheets", visuals=loose))

    # Assign grid positions to emitted visuals on each page.
    for page in pages:
        emitted = [v for v in page.visuals if v.emitted]
        for v, pos in zip(emitted, _grid_positions(len(emitted)), strict=False):
            v.position = pos
    return pages


def extract_from_twb(twb_path: Path, entity: str, columns: list[str]) -> list[PageNode]:
    root = ET.parse(twb_path).getroot()
    return extract(root, entity, columns)
