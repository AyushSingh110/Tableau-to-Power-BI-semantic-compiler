"""Reference evaluator for scalar measures over the Hyper extract data.

IMPORTANT — threat to validity (see docs/EVALUATION.md): this evaluator walks
the SAME AST that the DAX generator walks. Agreement between this evaluator and
Tableau therefore validates the *parser/IR*, not the generated DAX string. A
misconception shared by both the AST and this evaluator would pass silently.
The only true anchor is hand-loading the generated model into Power BI /
Tabular Editor and comparing to Tableau ("engine-verified"). This module
produces the weaker "proxy" number and must be reported as such.

Scope: grand-total scalars for aggregation / binary-of-aggregation / constant
measures. Row-level columns, conditionals, and functions are not evaluated
here and are reported as ``not_evaluated``.
"""

from __future__ import annotations

import pandas as pd

_AGG_REDUCE = {
    "SUM": lambda s: s.sum(),
    "AVG": lambda s: s.mean(),
    "MIN": lambda s: s.min(),
    "MAX": lambda s: s.max(),
    "COUNT": lambda s: s.count(),
    "COUNTD": lambda s: s.nunique(dropna=True),
    "MEDIAN": lambda s: s.median(),
}


class NotEvaluable(Exception):
    """Raised when a node cannot be reduced to a grand-total scalar here."""


def evaluate(node: dict, tables: dict[str, pd.DataFrame]) -> float:
    """Evaluate a scalar AST node against per-table DataFrames."""
    kind = node.get("node")

    if kind == "constant":
        if node["dtype"] == "number":
            return float(node["value"])
        raise NotEvaluable("non-numeric constant")

    if kind == "aggregation":
        arg = node["arg"]
        if arg.get("node") != "field":
            raise NotEvaluable("aggregation over non-field")
        agg = node["agg"]
        if agg not in _AGG_REDUCE:
            raise NotEvaluable(f"aggregation {agg}")
        table, col = arg.get("table"), arg["name"]
        if not table or table not in tables:
            raise NotEvaluable("unresolved table")
        series = pd.to_numeric(tables[table][col], errors="coerce") if agg not in ("COUNT", "COUNTD") else tables[table][col]
        return float(_AGG_REDUCE[agg](series))

    if kind == "binary":
        left = evaluate(node["left"], tables)
        right = evaluate(node["right"], tables)
        op = node["op"]
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right if right != 0 else float("nan")
        raise NotEvaluable(f"operator {op}")

    if kind == "unary":
        return -evaluate(node["operand"], tables)

    raise NotEvaluable(f"node {kind}")
