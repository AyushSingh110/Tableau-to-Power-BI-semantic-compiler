"""End-to-end: .twbx -> a full .pbip (SemanticModel TMDL + Report PBIR).

Unifies the two halves: the emitted report's visuals bind to the SAME entities
the emitted TMDL model exposes (the real multi-table names, e.g.
``Orders_ECFCA…``), so the project opens in Power BI Desktop with the compiler's
own model AND its own visuals, coherently bound.

Additive: reuses the shipped data-model pipeline and V1 visual emitter; the
existing ``run`` and ``visual`` commands are untouched.
"""

from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

from . import pipeline
from .export import tmdl
from .logging_config import get_logger
from .visual import emit_pbir, extract, layout, report

log = get_logger(__name__)

PBIP_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/pbip/1.0.0/schema.json"


def _twb_from_twbx(twbx: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="pbip_"))
    with zipfile.ZipFile(twbx) as z:
        z.extractall(tmp)
    return next(tmp.rglob("*.twb"))


def _load(data_dir: Path, name: str):
    return json.loads((data_dir / name).read_text(encoding="utf-8"))


def run(twbx_path: Path, out_dir: Path, name: str = "Superstore",
        data_dir: Path = Path("data"), csv_dir: Path | None = None) -> dict:
    twbx_path, out_dir, data_dir = Path(twbx_path), Path(out_dir), Path(data_dir)
    csv_dir = Path(csv_dir) if csv_dir else data_dir / "tables"

    # 1) Data-model pipeline (writes data/*.json + per-table CSVs).
    pipeline.run(twbx_path=twbx_path, data_dir=data_dir)

    hyper_schema = _load(data_dir, "parsed_hyper_schema.json")
    final_model = _load(data_dir, "final_powerbi_semantic_model.json")
    inferred = _load(data_dir, "inferred_powerbi_relationships.json")
    mappings = _load(data_dir, "logical_physical_mapping.json")
    sem_tables = _load(data_dir, "semantic_model.json")["tables"]

    # 2) TMDL semantic model.
    sm_dir = out_dir / f"{name}.SemanticModel"
    tmdl_info = tmdl.run(hyper_schema, final_model, inferred, sm_dir, csv_dir)

    # 3) Coherent multi-table visuals + dashboard layout.
    twb = _twb_from_twbx(twbx_path)
    pages = extract.extract_from_twb_multitable(twb, mappings, sem_tables)
    import xml.etree.ElementTree as ET
    layout.apply(ET.parse(twb).getroot(), pages)

    # 4) PBIR report bound to the emitted model.
    report_dir = out_dir / f"{name}.Report"
    emit_info = emit_pbir.emit(pages, report_dir, model_path=f"../{name}.SemanticModel")
    visual_report = report.build_report(pages)

    # 5) .pbip pointer.
    (out_dir / f"{name}.pbip").write_text(json.dumps({
        "$schema": PBIP_SCHEMA, "version": "1.0",
        "artifacts": [{"report": {"path": f"{name}.Report"}}], "settings": {},
    }, indent=2), encoding="utf-8")

    combined = {
        "pbip": str(out_dir / f"{name}.pbip"),
        "render_verified": "pending (open the .pbip in Power BI Desktop — see docs/VISUAL.md render-gate)",
        "model": {
            "conversion_report": final_model.get("conversion_report", {}),
            "tmdl": {k: v for k, v in tmdl_info.items() if k != "skipped_multiline"},
            "tmdl_skipped_multiline": tmdl_info.get("skipped_multiline", []),
        },
        "visuals": {
            **{k: visual_report[k] for k in (
                "worksheets_total", "visuals_emitted", "visuals_skipped",
                "emitted_by_type", "skipped_by_bucket", "coverage_pct_schema_valid")},
            "schema_validation": emit_info["schema_validation"],
            "bound_entities_are_multitable": True,
        },
    }
    (out_dir / "build_report.json").write_text(json.dumps(combined, indent=2), encoding="utf-8")
    log.info("Built .pbip at %s", out_dir / f"{name}.pbip")
    return combined
