"""Emit a Power BI Tabular Object Model (TOM) document.

Measures without a reliable owning table are not attached (which would be an
invalid guess); they are recorded as annotations so nothing disappears
silently.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

COMPATIBILITY_LEVEL = 1567


def _dax_type(raw: str) -> str:
    raw = raw.lower()
    if "int" in raw:
        return "int64"
    if "double" in raw or "float" in raw or "numeric" in raw:
        return "double"
    if "date" in raw or "time" in raw:
        return "dateTime"
    return "string"


def run(final_model: dict, hyper_schema: list[dict], data_dir: Path) -> dict:
    type_lookup = {
        (table["table"], col["column_name"]): _dax_type(col["data_type"])
        for table in hyper_schema
        for col in table["columns"]
    }

    tom = {
        "name": "Tableau_Migrated_Model",
        "compatibilityLevel": COMPATIBILITY_LEVEL,
        "model": {"tables": [], "relationships": [], "annotations": []},
    }

    for table_name, table_info in final_model["tables"].items():
        tom["model"]["tables"].append(
            {
                "name": table_name,
                "columns": [
                    {
                        "name": col,
                        "dataType": type_lookup.get((table_name, col), "string"),
                        "sourceColumn": col,
                    }
                    for col in table_info["columns"]
                ],
                "measures": [],
            }
        )

    table_map = {t["name"]: t for t in tom["model"]["tables"]}
    measure_table_map = final_model.get("measure_table_map", {})

    for measure_name, dax_expr in final_model["measures"].items():
        target = measure_table_map.get(measure_name)
        if not target or target not in table_map:
            tom["model"]["annotations"].append(
                {"name": f"UnplacedMeasure::{measure_name}", "value": "No reliable table context"}
            )
            continue
        table_map[target]["measures"].append(
            {"name": measure_name, "expression": dax_expr, "formatString": "General"}
        )

    for rel in final_model.get("relationships", []):
        tom["model"]["relationships"].append(
            {
                "fromTable": rel["from_table"],
                "fromColumn": rel["from_column"],
                "toTable": rel["to_table"],
                "toColumn": rel["to_column"],
                "cardinality": rel["cardinality"],
                "crossFilteringBehavior": rel["cross_filter_direction"],
            }
        )

    # Record skipped measures as annotations so the TOM is self-documenting.
    for skipped in final_model.get("conversion_report", {}).get("skipped_measures", []):
        tom["model"]["annotations"].append(
            {
                "name": f"SkippedMeasure::{skipped['calculation_name']}",
                "value": skipped["reason"],
            }
        )
    tom["model"]["annotations"].append(
        {
            "name": "MigrationNote",
            "value": "Generated via deterministic Tableau → Power BI semantic pipeline (tab2pbi)",
        }
    )

    with open(data_dir / "powerbi_tom_model.json", "w", encoding="utf-8") as f:
        json.dump(tom, f, indent=4)

    placed = sum(len(t["measures"]) for t in tom["model"]["tables"])
    log.info(
        "TOM export: %d tables, %d placed measures, %d relationships",
        len(tom["model"]["tables"]),
        placed,
        len(tom["model"]["relationships"]),
    )
    return tom
