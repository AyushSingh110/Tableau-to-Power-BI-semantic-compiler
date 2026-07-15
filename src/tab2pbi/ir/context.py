"""Resolve field table ownership within each measure AST.

Annotates every ``field`` node in every measure with its owning physical table
(from the logical→physical mapping). Ambiguous fields prefer the fact table.
The transpiler (``rewrite/dax``) consumes these annotations to emit
table-qualified DAX and to decide measure vs. calculated-column placement.
"""

import json
from collections import defaultdict
from pathlib import Path

from ..logging_config import get_logger
from .ast_utils import iter_fields

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


def run(semantic_model: dict, mappings: list[dict], data_dir: Path) -> dict:
    """Annotate measure ASTs with field table context and persist the model."""
    tables = semantic_model["tables"]
    field_to_table = build_field_to_table(mappings, tables)

    # Constant Tableau parameters (e.g. Parameter 1 = 2022). A field that names
    # one is inlined to its current constant value — a faithful snapshot (the
    # faithful interactive target is a Power BI What-If parameter; annotated
    # elsewhere). This unlocks parameter-driven measures like YoY.
    param_consts = {
        normalize_field_name(name): m["ast"]
        for name, m in semantic_model["measures"].items()
        if m["ast"].get("node") == "constant"
    }
    inlined = 0
    for measure in semantic_model["measures"].values():
        for field in iter_fields(measure["ast"]):
            key = normalize_field_name(field.get("name"))
            const = param_consts.get(key)
            if const is not None:
                field.clear()
                field.update(const)   # mutate field node -> constant node
                inlined += 1

    annotated = 0
    for measure in semantic_model["measures"].values():
        for field in iter_fields(measure["ast"]):   # re-walk: inlined ones are gone
            field["table"] = field_to_table.get(normalize_field_name(field.get("name")))
            if field["table"]:
                annotated += 1

    with open(data_dir / "semantic_model_with_context.json", "w", encoding="utf-8") as f:
        json.dump(semantic_model, f, indent=4)

    log.info(
        "Table context resolved: %d fields mapped, %d field refs annotated",
        len(field_to_table),
        annotated,
    )
    return semantic_model
