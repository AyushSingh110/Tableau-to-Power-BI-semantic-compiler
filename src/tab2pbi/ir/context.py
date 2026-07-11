"""Resolve measure table ownership and table-qualified DAX.

Enriches each measure AST with the owning physical table (from the
logical→physical mapping), regenerates table-qualified DAX, and records a
measure→table ownership map. Ambiguous fields prefer the fact table.
"""

import json
from collections import defaultdict
from pathlib import Path

from ..logging_config import get_logger
from ..rewrite.dax import ast_to_dax

log = get_logger(__name__)


def normalize_field_name(field: str | None) -> str | None:
    if not field:
        return None
    return field.strip().strip("[]").lower()


def build_field_to_table(mappings: list[dict], tables: dict) -> dict:
    """Resolve each logical field to a single owning table (fact preferred)."""
    field_to_tables = defaultdict(set)
    for m in mappings:
        field_to_tables[normalize_field_name(m["logical_field"])].add(m["table"])

    resolved = {}
    for field, owning in field_to_tables.items():
        if len(owning) == 1:
            resolved[field] = next(iter(owning))
        else:
            facts = [t for t in owning if tables.get(t, {}).get("type") == "fact"]
            resolved[field] = facts[0] if facts else sorted(owning)[0]
    return resolved


def _enrich(ast: dict, field_to_table: dict) -> dict:
    node = ast.get("node")
    if node == "single":
        ast["table"] = field_to_table.get(normalize_field_name(ast.get("field")))
    elif node == "binary":
        for side in ("left", "right"):
            child = ast.get(side, {})
            child["table"] = field_to_table.get(normalize_field_name(child.get("field")))
    return ast


def _owning_table(ast: dict) -> str | None:
    if ast.get("node") == "single":
        return ast.get("table")
    if ast.get("node") == "binary":
        return ast.get("left", {}).get("table")
    return None


def run(semantic_model: dict, mappings: list[dict], data_dir: Path) -> dict:
    """Enrich the semantic model with table context and persist it."""
    tables = semantic_model["tables"]
    field_to_table = build_field_to_table(mappings, tables)

    dax_measures = {}
    measure_table_map = {}
    for name, measure in semantic_model["measures"].items():
        measure["ast"] = _enrich(measure["ast"], field_to_table)
        dax, reason = ast_to_dax(measure["ast"])
        dax_measures[name] = dax if dax is not None else f"-- SKIPPED: {reason}"
        owner = _owning_table(measure["ast"])
        if owner:
            measure_table_map[name] = owner

    semantic_model["dax_measures"] = dax_measures
    semantic_model["measure_table_map"] = measure_table_map

    with open(data_dir / "semantic_model_with_context.json", "w", encoding="utf-8") as f:
        json.dump(semantic_model, f, indent=4)

    log.info(
        "Table context resolved: %d fields mapped, %d measures owned",
        len(field_to_table),
        len(measure_table_map),
    )
    return semantic_model
