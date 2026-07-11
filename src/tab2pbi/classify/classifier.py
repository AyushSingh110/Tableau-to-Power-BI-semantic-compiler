"""Per-measure convertibility report, aligned with transpiler outcomes.

Report-only: no stage depends on this file. It records, for every calculation,
how the transpiler actually treated it (measure / calculated column / parameter
/ skipped-with-taxonomy) alongside its formula, so the audit trail is complete.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def run(semantic_model: dict, converted: dict, data_dir: Path) -> list[dict]:
    """Emit ``calculation_classification.json`` from transpiler results."""
    formulas = {name: m.get("formula", "") for name, m in semantic_model["measures"].items()}

    classified: list[dict] = []
    for name in converted["measures"]:
        classified.append({"calculation_name": name, "formula": formulas.get(name, ""),
                            "classification": "measure", "note": "aggregation → DAX measure"})
    for col in converted["calculated_columns"]:
        classified.append({"calculation_name": col["name"], "formula": formulas.get(col["name"], ""),
                            "classification": "calculated_column", "note": "row-level → DAX calculated column"})
    for p in converted["parameters"]:
        classified.append({"calculation_name": p["name"], "formula": formulas.get(p["name"], ""),
                            "classification": "parameter", "note": p["note"]})
    for s in converted["skipped_measures"]:
        classified.append({"calculation_name": s["calculation_name"], "formula": formulas.get(s["calculation_name"], ""),
                            "classification": s["taxonomy"], "note": s["reason"]})

    with open(data_dir / "calculation_classification.json", "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=4)

    counts: dict[str, int] = {}
    for c in classified:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    log.info("Classified %d calculations: %s", len(classified), counts)
    return classified
