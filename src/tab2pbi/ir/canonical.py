"""Assemble the tool-agnostic canonical Power BI model."""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def run(
    hyper_schema: list[dict],
    context_model: dict,
    inferred_relationships: dict,
    data_dir: Path,
) -> dict:
    relationships = inferred_relationships.get("relationships", [])
    model_type = "flat_extract" if not relationships else "relational_model"

    tables = {
        entry["table"]: {
            "columns": [c["column_name"] for c in entry["columns"]],
            "type": context_model["tables"].get(entry["table"], {}).get("type"),
            "source": "tableau_hyper",
        }
        for entry in hyper_schema
    }

    canonical = {
        "model_type": model_type,
        "tables": tables,
        "measures": context_model.get("dax_measures", {}),
        "relationships": relationships,
        "provenance": {
            **context_model.get("provenance", {}),
            "relationship_inference": "data-driven",
            "engine_assumptions": "none",
        },
    }
    with open(data_dir / "canonical_powerbi_model.json", "w", encoding="utf-8") as f:
        json.dump(canonical, f, indent=4)
    log.info(
        "Canonical model: type=%s, %d tables, %d relationships",
        model_type,
        len(tables),
        len(relationships),
    )
    return canonical
