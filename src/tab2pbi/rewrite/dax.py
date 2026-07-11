"""AST → DAX translation and the ``rewrite`` stage.

This module owns the single source of truth for turning a context-enriched AST
node into DAX. A node is only translated when it is a recognised shape *and*
every referenced field has a resolved owning table; otherwise it is skipped
with a reason so the audit trail stays complete.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

# Tableau aggregation → DAX function.
_AGG_TO_DAX = {
    "SUM": "SUM",
    "AVG": "AVERAGE",
    "MIN": "MIN",
    "MAX": "MAX",
    "COUNT": "COUNT",
    "COUNTD": "DISTINCTCOUNT",
}


def _agg_term(agg: str, table: str, field: str) -> str:
    return f"{_AGG_TO_DAX[agg.upper()]}({table}[{field}])"


def ast_to_dax(ast: dict) -> tuple[str | None, str | None]:
    """Translate a context-enriched AST node to DAX.

    Returns ``(dax, None)`` on success or ``(None, reason)`` when the node
    cannot be translated.
    """
    node = ast.get("node")

    if node == "single":
        table = ast.get("table")
        if not table:
            return None, "unresolved_table_context"
        return _agg_term(ast["agg"], table, ast["field"]), None

    if node == "binary":
        left, right = ast["left"], ast["right"]
        if not left.get("table") or not right.get("table"):
            return None, "unresolved_table_context"
        dax = (
            f"{_agg_term(left['agg'], left['table'], left['field'])} "
            f"{ast['op']} "
            f"{_agg_term(right['agg'], right['table'], right['field'])}"
        )
        return dax, None

    return None, ast.get("reason", "unsupported_expression")


def run(context_model: dict, data_dir: Path) -> dict:
    """Translate all measures, writing ``converted_dax_measures.json``."""
    converted: dict[str, str] = {}
    skipped: list[dict] = []

    for name, measure in context_model["measures"].items():
        dax, reason = ast_to_dax(measure["ast"])
        if dax is not None:
            converted[name] = dax
        else:
            skipped.append({"calculation_name": name, "reason": reason})

    output = {"converted_measures": converted, "skipped_measures": skipped}
    with open(data_dir / "converted_dax_measures.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    log.info("DAX rewrite: %d converted, %d skipped", len(converted), len(skipped))
    return output
