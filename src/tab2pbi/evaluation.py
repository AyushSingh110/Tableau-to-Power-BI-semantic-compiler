"""Reference evaluator for scalar measures over the Hyper extract data.

IMPORTANT — threat to validity (see docs/EVALUATION.md): this evaluator walks
the SAME AST that the DAX generator walks. Agreement between this evaluator and
Tableau therefore validates the *parser/IR*, not the generated DAX string. A
misconception shared by both the AST and this evaluator would pass silently.
The only true anchor is hand-loading the generated model into Power BI /
Tabular Editor and comparing to Tableau ("engine-verified"). This module
produces the weaker "proxy" number and must be reported as such.

Scope: grand-total scalars for aggregation / binary-of-aggregation / constant
measures, plus **conditional (row-level) aggregations** — e.g.
``SUM(ZN(IF YEAR=2022 THEN Sales))`` — evaluated with a small row-wise engine so
the SUMX-form converters are proxy-checkable. Anything outside this is still
reported as ``not_evaluated``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .ir.ast_utils import field_tables

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
        agg = node["agg"]
        if agg not in _AGG_REDUCE:
            raise NotEvaluable(f"aggregation {agg}")
        if arg.get("node") == "field":
            table, col = arg.get("table"), arg["name"]
            if not table or table not in tables:
                raise NotEvaluable("unresolved table")
            series = tables[table][col] if agg in ("COUNT", "COUNTD") else pd.to_numeric(tables[table][col], errors="coerce")
            return float(_AGG_REDUCE[agg](series))
        # aggregation over a row-level expression -> reduce the per-row Series.
        ts = field_tables(arg)
        if len(ts) != 1:
            raise NotEvaluable("aggregation over expr spanning multiple/zero tables")
        df = tables[next(iter(ts))]
        series = pd.to_numeric(_row(arg, df), errors="coerce")
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


def _num(v):
    return pd.to_numeric(v, errors="coerce") if isinstance(v, pd.Series) else v


def _row(node: dict, df: pd.DataFrame):
    """Evaluate a node to a per-row pandas Series (or scalar) over ``df``."""
    kind = node.get("node")
    if kind == "constant":
        return node["value"]
    if kind == "field":
        return df[node["name"]]
    if kind == "unary":
        return -_num(_row(node["operand"], df))
    if kind == "binary":
        left, right = _num(_row(node["left"], df)), _num(_row(node["right"], df))
        op = node["op"]
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        raise NotEvaluable(f"row operator {op}")
    if kind == "comparison":
        left, right = _num(_row(node["left"], df)), _num(_row(node["right"], df))
        op = node["op"]
        cmp = {"=": left == right, "<>": left != right, "<": left < right,
               ">": left > right, "<=": left <= right, ">=": left >= right}
        if op not in cmp:
            raise NotEvaluable(f"row comparison {op}")
        return cmp[op]
    if kind == "conditional":
        otherwise = _row(node["otherwise"], df) if node.get("otherwise") is not None else np.nan
        result = pd.Series(otherwise, index=df.index) if not isinstance(otherwise, pd.Series) else otherwise.copy()
        for br in reversed(node["branches"]):
            cond = _row(br["when"], df)
            then = _row(br["then"], df)
            result = result.mask(cond, then)
        return result
    if kind == "function":
        name, args = node["name"], node.get("args", [])
        if name == "ZN" and len(args) == 1:
            return _num(_row(args[0], df)).fillna(0)
        if name in ("YEAR", "MONTH", "DAY") and len(args) == 1:
            dt = pd.to_datetime(_row(args[0], df), errors="coerce")
            return getattr(dt.dt, name.lower())
        raise NotEvaluable(f"row function {name}")
    raise NotEvaluable(f"row node {kind}")
