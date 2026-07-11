"""Map Tableau logical fields to Hyper physical columns.

Deterministic, case-insensitive exact-name matching only. No inferred aliases
or heuristic matching: if a logical field has no exact physical counterpart it
simply is not mapped (and therefore later reported as un-owned rather than
guessed).
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)


def map_logical_to_physical(datasources: list[dict], hyper_schema: list[dict]) -> list[dict]:
    """Return exact logical→physical column mappings (deduplicated)."""
    seen = set()
    mappings = []
    for ds in datasources:
        for field in ds["fields"]:
            lf = field["field_name"]
            if not lf:
                continue
            for table in hyper_schema:
                for col in table["columns"]:
                    pc = col["column_name"]
                    if pc and lf.lower() == pc.lower():
                        key = (lf, pc, table["table"])
                        if key not in seen:
                            seen.add(key)
                            mappings.append(
                                {
                                    "logical_field": lf,
                                    "physical_column": pc,
                                    "table": table["table"],
                                    "schema": table["schema"],
                                }
                            )
    return mappings


def run(datasources: list[dict], hyper_schema: list[dict], data_dir: Path) -> list[dict]:
    """Build the logical→physical mapping and write it to ``data_dir``."""
    mappings = map_logical_to_physical(datasources, hyper_schema)
    with open(data_dir / "logical_physical_mapping.json", "w", encoding="utf-8") as f:
        json.dump(mappings, f, indent=4)
    log.info("Logical→physical mappings: %d", len(mappings))
    return mappings
