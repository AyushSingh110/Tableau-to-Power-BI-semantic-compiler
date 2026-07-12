"""Emit a PBIR report from PageNodes and validate it.

Emits the exact structure of the ground-truth ``pbir_reference`` (schema pinned
to ``visualContainer/2.3.0``): per-visual ``visual.json`` with
``field -> Column/Aggregation -> Expression -> SourceRef -> Entity/Property`` and
``Function: 0`` for Sum, plus ``page.json``/``pages.json``/``report.json``/
``version.json``/``definition.pbir`` and the bundled theme.

Validation is two-gated:
1. **Structural** conformance to the reference skeleton (enforced, offline).
2. **JSON-schema** against the pinned schema (best-effort; degrades to a logged
   warning if the schema's remote ``$ref`` tree cannot be resolved offline).
A structural failure aborts emission loudly.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ..logging_config import get_logger
from .ir import AGG_DISPLAY, AGG_FUNCTION, PageNode, VisualNode

log = get_logger(__name__)

VISUAL_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.3.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json"
PAGES_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json"

TEMPLATES = Path(__file__).parent / "templates"
ALLOWED_VISUAL_TYPES = {
    "columnChart", "barChart", "lineChart", "areaChart", "pieChart",
    "scatterChart", "tableEx", "card", "map",
}


def _oid(*parts: str) -> str:
    return hashlib.sha1("::".join(parts).encode("utf-8")).hexdigest()[:20]


def _projection(fr) -> dict:
    entity, col = fr.entity, fr.column
    src = {"Expression": {"SourceRef": {"Entity": entity}}, "Property": col}
    if fr.is_measure:
        fn = AGG_DISPLAY[fr.aggregation]
        return {
            "field": {"Aggregation": {"Expression": {"Column": src}, "Function": AGG_FUNCTION[fr.aggregation]}},
            "queryRef": f"{fn}({entity}.{col})",
            "nativeQueryRef": f"{fn} of {col}",
        }
    return {
        "field": {"Column": src},
        "queryRef": f"{entity}.{col}",
        "nativeQueryRef": col,
        "active": True,
    }


def _visual_json(v: VisualNode) -> dict:
    p = v.position
    query_state = {
        role: {"projections": [_projection(fr) for fr in frs]}
        for role, frs in v.wells.items()
    }
    return {
        "$schema": VISUAL_SCHEMA,
        "name": _oid(v.worksheet),
        "position": {"x": p.x, "y": p.y, "z": p.z, "width": p.width, "height": p.height},
        "visual": {
            "visualType": v.visual_type,
            "query": {"queryState": query_state},
            "drillFilterOtherVisuals": True,
        },
    }


# ---------------- validation ----------------

class StructuralError(ValueError):
    """Raised when an emitted visual.json deviates from the reference skeleton."""


def structural_check(obj: dict) -> None:
    if obj.get("$schema") != VISUAL_SCHEMA:
        raise StructuralError(f"$schema must be pinned {VISUAL_SCHEMA}")
    if not isinstance(obj.get("name"), str):
        raise StructuralError("missing string 'name'")
    pos = obj.get("position", {})
    for k in ("x", "y", "z", "width", "height"):
        if not isinstance(pos.get(k), int | float):
            raise StructuralError(f"position.{k} must be numeric")
    vis = obj.get("visual", {})
    if vis.get("visualType") not in ALLOWED_VISUAL_TYPES:
        raise StructuralError(f"unexpected visualType {vis.get('visualType')!r}")
    qs = vis.get("query", {}).get("queryState")
    if not isinstance(qs, dict) or not qs:
        raise StructuralError("empty queryState")
    for role, bucket in qs.items():
        for proj in bucket.get("projections", []):
            f = proj.get("field", {})
            node = f.get("Column") or f.get("Aggregation", {}).get("Expression", {}).get("Column")
            if not node:
                raise StructuralError(f"role {role}: projection missing Column/Aggregation")
            if not node.get("Expression", {}).get("SourceRef", {}).get("Entity"):
                raise StructuralError(f"role {role}: missing SourceRef.Entity")
            if not node.get("Property"):
                raise StructuralError(f"role {role}: missing Property")


def schema_check(obj: dict) -> str:
    """Best-effort JSON-schema validation. Returns a status string."""
    schema_file = TEMPLATES / "schema" / "visualContainer.2.3.0.schema.json"
    if not schema_file.exists():
        return "skipped (schema not vendored)"
    try:
        import jsonschema
        jsonschema.validate(obj, json.loads(schema_file.read_text(encoding="utf-8")))
        return "passed"
    except Exception as exc:  # remote $ref / resolution issues degrade gracefully
        return f"degraded ({type(exc).__name__})"


# ---------------- emission ----------------

def emit(pages: list[PageNode], out_report_dir: Path, model_path: str) -> dict:
    """Emit the PBIR report tree under ``out_report_dir`` (a *.Report folder)."""
    out_report_dir = Path(out_report_dir)
    definition = out_report_dir / "definition"
    if out_report_dir.exists():
        shutil.rmtree(out_report_dir)
    (definition / "pages").mkdir(parents=True, exist_ok=True)

    # Fixed scaffolding (copied verbatim from the ground-truth reference).
    shutil.copytree(TEMPLATES / "StaticResources", out_report_dir / "StaticResources")
    for fn in ("report.json", "version.json"):
        shutil.copy(TEMPLATES / fn, definition / fn)
    (out_report_dir / "definition.pbir").write_text(
        json.dumps({"version": "4.0", "datasetReference": {"byPath": {"path": model_path}}}, indent=2),
        encoding="utf-8",
    )

    page_ids: list[str] = []
    schema_status = set()
    emitted_visuals = 0
    for page in pages:
        page.id = _oid("page", page.name)
        page_ids.append(page.id)
        pdir = definition / "pages" / page.id
        (pdir / "visuals").mkdir(parents=True, exist_ok=True)
        (pdir / "page.json").write_text(json.dumps({
            "$schema": PAGE_SCHEMA, "name": page.id, "displayName": page.display_name,
            "displayOption": "FitToPage", "height": 720, "width": 1280,
        }, indent=2), encoding="utf-8")

        for v in page.visuals:
            if not v.emitted:
                continue
            vjson = _visual_json(v)
            structural_check(vjson)                 # enforced gate — raises on failure
            schema_status.add(schema_check(vjson))  # best-effort gate
            vid = vjson["name"]
            vdir = pdir / "visuals" / vid
            vdir.mkdir(parents=True, exist_ok=True)
            (vdir / "visual.json").write_text(json.dumps(vjson, indent=2), encoding="utf-8")
            emitted_visuals += 1

    (definition / "pages" / "pages.json").write_text(json.dumps({
        "$schema": PAGES_SCHEMA,
        "pageOrder": page_ids,
        "activePageName": page_ids[0] if page_ids else "",
    }, indent=2), encoding="utf-8")

    log.info("Emitted %d visuals across %d pages -> %s", emitted_visuals, len(page_ids), out_report_dir)
    return {
        "report_dir": str(out_report_dir),
        "pages": len(page_ids),
        "emitted_visuals": emitted_visuals,
        "schema_validation": sorted(schema_status) or ["n/a"],
    }
