"""Merge transpiler output into the auditable final semantic model.

The final model carries measures, calculated columns, and parameters that were
actually translated to DAX. Skipped calculations are never dropped silently —
they are listed with reasons and a machine-readable failure taxonomy in
``conversion_report``. When the fact table was inferred by size (a heuristic,
not a declaration), every measure owned by that table is flagged.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

# Canonical failure-taxonomy buckets (always present, zero-filled).
TAXONOMY_BUCKETS = [
    "lod_expression", "table_calc", "window_fn", "custom_sql",
    "parse_error", "unsupported_fn", "unresolved", "aggregate_of_expression",
    "empty_formula",
]


def run(canonical: dict, context_model: dict, converted: dict,
        classification: list[dict], data_dir: Path) -> dict:
    model = dict(canonical)

    measures = converted["measures"]
    measure_table_map = converted["measure_table_map"]
    columns = converted["calculated_columns"]
    parameters = converted["parameters"]
    skipped = converted["skipped_measures"]

    model["measures"] = measures
    model["measure_table_map"] = measure_table_map
    model["calculated_columns"] = columns
    model["parameters"] = parameters

    # Failure taxonomy counts (zero-filled so every bucket is explicit).
    taxonomy = {b: 0 for b in TAXONOMY_BUCKETS}
    for s in skipped:
        taxonomy[s["taxonomy"]] = taxonomy.get(s["taxonomy"], 0) + 1

    total = len(measures) + len(columns) + len(parameters) + len(skipped)

    # Flag measures owned by a fact table that was inferred, not declared.
    fact_info = context_model.get("provenance", {}).get("fact_table_inference", {})
    fact_notes = []
    if fact_info.get("method") == "inferred_by_size":
        fact_table = fact_info.get("table")
        for name, owner in measure_table_map.items():
            if owner == fact_table:
                fact_notes.append({"measure": name, "table": fact_table,
                                   "note": "fact table inferred by size, not declared"})

    model["conversion_report"] = {
        "total_calculations": total,
        "measures_converted": len(measures),
        "columns_converted": len(columns),
        "parameters_converted": len(parameters),
        "skipped_count": len(skipped),
        "coverage_pct": round(100 * (len(measures) + len(columns)) / total, 1) if total else 0.0,
        "skipped_measures": skipped,
        "failure_taxonomy": taxonomy,
        "fact_table_inference": fact_info,
        "measures_affected_by_fact_inference": fact_notes,
    }

    with open(data_dir / "final_powerbi_semantic_model.json", "w", encoding="utf-8") as f:
        json.dump(model, f, indent=4)

    log.info(
        "Final model: %d measures, %d columns, %d parameters, %d skipped (coverage %.1f%%)",
        len(measures), len(columns), len(parameters), len(skipped),
        model["conversion_report"]["coverage_pct"],
    )
    return model
