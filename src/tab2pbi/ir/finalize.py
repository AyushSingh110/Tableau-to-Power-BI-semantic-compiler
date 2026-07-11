"""Merge measures and build the auditable final semantic model.

The final model carries only measures that were actually translated to DAX.
Skipped measures are never dropped silently — they are listed with reasons in
``conversion_report``. When the fact table was inferred by size (a heuristic,
not a declaration), every measure owned by that table is flagged here.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def run(
    canonical: dict,
    context_model: dict,
    converted: dict,
    classification: list[dict],
    data_dir: Path,
) -> dict:
    model = dict(canonical)
    measure_table_map = context_model.get("measure_table_map", {})
    model["measure_table_map"] = measure_table_map

    converted_measures = converted.get("converted_measures", {})
    skipped_measures = converted.get("skipped_measures", [])
    model["measures"] = converted_measures

    # Classification breakdown (report-only taxonomy).
    class_counts: dict[str, int] = {}
    for c in classification:
        class_counts[c["classification"]] = class_counts.get(c["classification"], 0) + 1

    # Flag measures owned by a fact table that was only inferred, not declared.
    fact_info = context_model.get("provenance", {}).get("fact_table_inference", {})
    fact_notes = []
    if fact_info.get("method") == "inferred_by_size":
        fact_table = fact_info.get("table")
        for name in converted_measures:
            if measure_table_map.get(name) == fact_table:
                fact_notes.append(
                    {
                        "measure": name,
                        "table": fact_table,
                        "note": "fact table inferred by size, not declared",
                    }
                )

    model["conversion_report"] = {
        "total_measures": len(converted_measures) + len(skipped_measures),
        "converted_count": len(converted_measures),
        "skipped_count": len(skipped_measures),
        "skipped_measures": skipped_measures,
        "classification_counts": class_counts,
        "fact_table_inference": fact_info,
        "measures_affected_by_fact_inference": fact_notes,
    }

    with open(data_dir / "final_powerbi_semantic_model.json", "w", encoding="utf-8") as f:
        json.dump(model, f, indent=4)
    log.info(
        "Final model: %d converted, %d skipped, %d measures flagged by fact inference",
        len(converted_measures),
        len(skipped_measures),
        len(fact_notes),
    )
    return model
