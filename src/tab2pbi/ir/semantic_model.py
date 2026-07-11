"""Build the AST-shaped semantic model — the previously-missing pipeline step.

Produces ``semantic_model.json`` in exactly the shape the context-resolution
stage expects: ``tables`` (each tagged fact/dimension), ``measures`` (each with
an ``ast``), plus ``dimensions``/``filters`` passthrough and a ``provenance``
block recording how the fact table was determined.

Fact-vs-dimension is a DOCUMENTED HEURISTIC, not declared truth. Precedence:

1. an explicit user override (``fact_table`` argument / ``--fact-table``),
2. a role declared by the workbook (Tableau .twbx files do not currently
   declare these, so this branch is reserved),
3. otherwise the largest table by column count ("inferred_by_size").

When the size heuristic is used, this is recorded in provenance and every
measure later found to be owned by that table is annotated downstream.
"""

import json
from pathlib import Path

from ..logging_config import get_logger
from .ast_builder import build_ast

log = get_logger(__name__)


def determine_fact_table(
    hyper_schema: list[dict],
    fact_table: str | None = None,
    declared_roles: dict[str, str] | None = None,
) -> dict:
    """Decide the fact table and record how the decision was made."""
    table_names = [e["table"] for e in hyper_schema]
    if not table_names:
        return {"table": None, "method": "no_tables", "note": "no physical tables found"}

    if fact_table:
        if fact_table not in table_names:
            raise ValueError(
                f"--fact-table {fact_table!r} is not a physical table. "
                f"Available: {', '.join(table_names)}"
            )
        return {
            "table": fact_table,
            "method": "user_override",
            "note": "fact table explicitly specified by user",
        }

    if declared_roles:
        facts = [t for t, r in declared_roles.items() if str(r).lower() == "fact"]
        if facts:
            return {
                "table": facts[0],
                "method": "declared",
                "note": "fact role declared by the workbook",
            }

    widest = max(hyper_schema, key=lambda e: len(e["columns"]))
    return {
        "table": widest["table"],
        "method": "inferred_by_size",
        "note": "fact table inferred by size (most columns), not declared",
    }


def build_tables(hyper_schema: list[dict], fact_info: dict) -> dict:
    """Build the table map, tagging the fact table and others as dimensions."""
    tables = {}
    for entry in hyper_schema:
        tables[entry["table"]] = {
            "columns": [c["column_name"] for c in entry["columns"]],
            "type": "fact" if entry["table"] == fact_info["table"] else "dimension",
            "source": "tableau_hyper",
        }
    return tables


def build_measures(datasources: list[dict]) -> dict:
    """Build the measure map (name → {ast, formula, source})."""
    measures = {}
    for ds in datasources:
        for calc in ds.get("calculations", []):
            name = calc["field_name"]
            if name is None:
                continue
            formula = calc.get("formula", "")
            measures[name] = {
                "ast": build_ast(formula),
                "formula": formula,
                "source": "tableau",
            }
    return measures


def run(
    datasources: list[dict],
    hyper_schema: list[dict],
    data_dir: Path,
    fact_table: str | None = None,
) -> dict:
    """Build and persist ``semantic_model.json``."""
    fact_info = determine_fact_table(hyper_schema, fact_table=fact_table)
    tables = build_tables(hyper_schema, fact_info)
    measures = build_measures(datasources)

    convertible = sum(
        1 for m in measures.values() if m["ast"]["node"] in ("single", "binary")
    )
    model = {
        "tables": tables,
        "measures": measures,
        "dimensions": {},
        "filters": [],
        "provenance": {
            "fact_table_inference": fact_info,
            "ast_builder": "phase1-regex",
        },
    }
    with open(data_dir / "semantic_model.json", "w", encoding="utf-8") as f:
        json.dump(model, f, indent=4)

    log.info(
        "Semantic model: %d tables (fact=%s via %s), %d measures (%d convertible AST shapes)",
        len(tables),
        fact_info["table"],
        fact_info["method"],
        len(measures),
        convertible,
    )
    return model
