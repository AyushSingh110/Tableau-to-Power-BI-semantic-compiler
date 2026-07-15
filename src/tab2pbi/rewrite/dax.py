"""AST → DAX transpiler and the ``rewrite`` stage.

Walks the context-enriched AST and emits DAX for the shapes it supports:
constants, aggregations of fields, arithmetic/comparison/logical combinations,
IF/CASE conditionals, and a small set of scalar/date functions. Anything else
raises :class:`TranspileError` carrying a machine-readable taxonomy category, so
the calculation is skipped with a precise, auditable reason — never fabricated.

Measures (AST contains an aggregation) become TOM measures; row-level
expressions become TOM calculated columns; pure constants are treated as
Tableau parameters and emitted as calculated columns with a note (a Power BI
What-If / field parameter is the more faithful target).
"""

import json
from pathlib import Path

from ..ir.ast_utils import field_tables, has_aggregation, has_field, has_measure_ref, iter_fields
from ..logging_config import get_logger

log = get_logger(__name__)


class TranspileError(Exception):
    """Raised when a node cannot be translated. Carries a taxonomy category."""

    def __init__(self, reason: str, taxonomy: str):
        super().__init__(reason)
        self.reason = reason
        self.taxonomy = taxonomy


# Tableau aggregation → DAX function.
_AGG_TO_DAX = {
    "SUM": "SUM", "AVG": "AVERAGE", "MIN": "MIN", "MAX": "MAX",
    "COUNT": "COUNT", "COUNTD": "DISTINCTCOUNT", "MEDIAN": "MEDIAN",
    "STDEV": "STDEV.S", "STDEVP": "STDEV.P", "VAR": "VAR.S", "VARP": "VAR.P",
}
# Aggregation over a row-level expression -> the iterator ("X") form.
_AGG_TO_X = {"SUM": "SUMX", "AVG": "AVERAGEX", "MIN": "MINX", "MAX": "MAXX", "COUNT": "COUNTX"}
_DATEDIFF_PART = {
    "day": "DAY", "days": "DAY", "month": "MONTH", "year": "YEAR",
    "quarter": "QUARTER", "week": "WEEK", "hour": "HOUR",
    "minute": "MINUTE", "second": "SECOND",
}
# Function-name → taxonomy category for known-unsupported families.
_WINDOW_FUNCS = {"WINDOW_SUM", "WINDOW_AVG", "WINDOW_MIN", "WINDOW_MAX",
                 "WINDOW_COUNT", "WINDOW_MEDIAN", "WINDOW_STDEV", "WINDOW_VAR"}
_TABLE_CALC_FUNCS = {"INDEX", "RANK", "RANK_UNIQUE", "RANK_DENSE", "RANK_MODIFIED",
                     "RANK_PERCENTILE", "RUNNING_SUM", "RUNNING_AVG", "RUNNING_MIN",
                     "RUNNING_MAX", "RUNNING_COUNT", "LOOKUP", "FIRST", "LAST",
                     "TOTAL", "SIZE", "PREVIOUS_VALUE"}
_CUSTOM_SQL_FUNCS = {"RAWSQL", "RAWSQLAGG", "RAWSQL_INT", "RAWSQL_REAL",
                     "RAWSQL_STR", "RAWSQL_DATE", "RAWSQL_DATETIME", "RAWSQL_BOOL"}


def _num(value) -> str:
    return str(int(value)) if isinstance(value, int) else repr(value)


def _dax_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def to_dax(node: dict) -> str:
    """Translate a context-enriched AST node to a DAX expression string."""
    kind = node.get("node")

    if kind == "constant":
        dtype = node["dtype"]
        if dtype == "number":
            return _num(node["value"])
        if dtype == "string":
            return _dax_string(node["value"])
        if dtype == "boolean":
            return "TRUE()" if node["value"] else "FALSE()"
        return "BLANK()"  # null

    if kind == "field":
        table = node.get("table")
        if not table:
            raise TranspileError(
                f"unresolved table for field [{node.get('name')}]", "unresolved"
            )
        return f"{table}[{node['name']}]"

    if kind == "measure_ref":
        return f"[{node['name']}]"

    if kind == "aggregation":
        arg = node["arg"]
        if arg.get("node") == "field":
            return f"{_AGG_TO_DAX[node['agg']]}({to_dax(arg)})"
        # aggregation over a row-level expression -> iterator form (SUMX/…),
        # e.g. SUM(ZN(IF year=2022 THEN Sales)) -> SUMX(Orders, COALESCE(IF(…),0)).
        if node["agg"] not in _AGG_TO_X:
            raise TranspileError(
                f"aggregation {node['agg']} over an expression", "aggregate_of_expression"
            )
        tables = field_tables(arg)
        if len(tables) != 1:
            raise TranspileError(
                "aggregation over an expression spanning multiple/zero tables",
                "aggregate_of_expression",
            )
        return f"{_AGG_TO_X[node['agg']]}({next(iter(tables))}, {to_dax(arg)})"

    if kind == "binary":
        return f"{to_dax(node['left'])} {node['op']} {to_dax(node['right'])}"

    if kind == "comparison":
        return f"{to_dax(node['left'])} {node['op']} {to_dax(node['right'])}"

    if kind == "logical":
        op = "&&" if node["op"] == "AND" else "||"
        return f"({to_dax(node['left'])} {op} {to_dax(node['right'])})"

    if kind == "not":
        return f"NOT({to_dax(node['operand'])})"

    if kind == "unary":
        return f"-{to_dax(node['operand'])}"

    if kind == "conditional":
        return _conditional_to_dax(node)

    if kind == "function":
        return _function_to_dax(node)

    if kind == "unsupported":
        raise TranspileError(node.get("reason", "unsupported"), node.get("reason", "unsupported"))
    if kind == "parse_error":
        raise TranspileError(node.get("reason", "parse error"), "parse_error")

    raise TranspileError(f"unhandled node {kind}", "unsupported_fn")


def _conditional_to_dax(node: dict) -> str:
    branches = node["branches"]
    otherwise = to_dax(node["otherwise"]) if node.get("otherwise") is not None else "BLANK()"
    if len(branches) == 1:
        b = branches[0]
        return f"IF({to_dax(b['when'])}, {to_dax(b['then'])}, {otherwise})"
    parts = ["SWITCH(TRUE()"]
    for b in branches:
        parts.append(f"{to_dax(b['when'])}, {to_dax(b['then'])}")
    parts.append(otherwise)
    return ", ".join(parts) + ")"


def _function_to_dax(node: dict) -> str:
    name = node["name"]
    args = node.get("args", [])

    if name in _WINDOW_FUNCS:
        raise TranspileError(f"window function {name}", "window_fn")
    if name in _TABLE_CALC_FUNCS:
        raise TranspileError(f"table calculation {name}", "table_calc")
    if name in _CUSTOM_SQL_FUNCS:
        raise TranspileError(f"custom SQL {name}", "custom_sql")

    if name == "DATEDIFF" and len(args) == 3:
        part_node = args[0]
        if part_node.get("node") != "constant" or part_node.get("dtype") != "string":
            raise TranspileError("DATEDIFF part must be a literal", "unsupported_fn")
        part = _DATEDIFF_PART.get(part_node["value"].lower())
        if not part:
            raise TranspileError(f"DATEDIFF part {part_node['value']!r}", "unsupported_fn")
        return f"DATEDIFF({to_dax(args[1])}, {to_dax(args[2])}, {part})"

    if name in ("YEAR", "MONTH", "DAY") and len(args) == 1:
        return f"{name}({to_dax(args[0])})"

    if name == "DATEPART" and len(args) == 2:
        part_node = args[0]
        if part_node.get("node") == "constant" and part_node.get("dtype") == "string":
            part = part_node["value"].lower()
            if part in ("year", "month", "day"):
                return f"{part.upper()}({to_dax(args[1])})"
        raise TranspileError("DATEPART part unsupported", "unsupported_fn")

    if name == "ABS" and len(args) == 1:
        return f"ABS({to_dax(args[0])})"
    if name == "ROUND" and len(args) in (1, 2):
        digits = to_dax(args[1]) if len(args) == 2 else "0"
        return f"ROUND({to_dax(args[0])}, {digits})"
    if name == "INT" and len(args) == 1:
        return f"INT({to_dax(args[0])})"
    if name == "ZN" and len(args) == 1:
        return f"COALESCE({to_dax(args[0])}, 0)"

    raise TranspileError(f"unsupported function {name}", "unsupported_fn")


def _skip(name: str, reason: str, taxonomy: str) -> dict:
    return {"calculation_name": name, "reason": reason, "taxonomy": taxonomy}


def analyze(name: str, ast: dict, fact_table: str | None) -> dict:
    """Classify one enriched measure AST and attempt transpilation."""
    kind = ast.get("node")
    if kind == "parse_error":
        return {"kind": "skipped", **_skip(name, ast.get("reason", "parse error"), "parse_error")}
    if kind == "unsupported":
        reason = ast.get("reason", "unsupported")
        return {"kind": "skipped", **_skip(name, reason, reason)}

    is_agg = has_aggregation(ast)
    is_field = has_field(ast)
    is_measure_ref = has_measure_ref(ast)

    # Pure constant → Tableau parameter.
    if not is_agg and not is_field and not is_measure_ref:
        try:
            dax = to_dax(ast)
        except TranspileError as e:
            return {"kind": "skipped", **_skip(name, e.reason, e.taxonomy)}
        return {
            "kind": "parameter",
            "name": name,
            "table": fact_table,
            "dax": dax,
            "note": "Tableau parameter; a Power BI What-If/field parameter is the faithful target",
        }

    # Aggregation, or a measure that references another measure -> a measure.
    if is_agg or is_measure_ref:
        try:
            dax = to_dax(ast)
        except TranspileError as e:
            return {"kind": "skipped", **_skip(name, e.reason, e.taxonomy)}
        tables = field_tables(ast)
        owner = fact_table if (fact_table in tables or not tables) else sorted(tables)[0]
        return {"kind": "measure", "name": name, "table": owner, "dax": dax}

    # Row-level expression → calculated column.
    tables = field_tables(ast)
    if len(tables) == 0:
        return {"kind": "skipped", **_skip(
            name, "references an unresolved field or another calculated field", "unresolved")}
    if len(tables) > 1:
        return {"kind": "skipped", **_skip(
            name, "row-level expression spans multiple tables", "unsupported_fn")}
    try:
        dax = to_dax(ast)
    except TranspileError as e:
        return {"kind": "skipped", **_skip(name, e.reason, e.taxonomy)}
    return {"kind": "column", "name": name, "table": next(iter(tables)), "dax": dax}


def run(context_model: dict, data_dir: Path) -> dict:
    """Transpile all measures, writing ``converted_dax_measures.json``."""
    fact_table = (
        context_model.get("provenance", {}).get("fact_table_inference", {}).get("table")
    )

    measures: dict[str, str] = {}
    measure_table_map: dict[str, str] = {}
    columns: list[dict] = []
    parameters: list[dict] = []
    skipped: list[dict] = []

    for name, measure in context_model["measures"].items():
        result = analyze(name, measure["ast"], fact_table)
        kind = result["kind"]
        if kind == "measure":
            measures[name] = result["dax"]
            if result["table"]:
                measure_table_map[name] = result["table"]
        elif kind == "column":
            columns.append({"name": name, "table": result["table"], "dax": result["dax"]})
        elif kind == "parameter":
            parameters.append(result)
        else:
            skipped.append({"calculation_name": name, "reason": result["reason"], "taxonomy": result["taxonomy"]})

    # Second pass — calc-to-calc: a measure skipped as `unresolved` because it
    # references another calc that we DID convert becomes a DAX measure
    # reference. Only converts if the dependency is itself convertible.
    converted_names = {k.strip().strip("[]").lower(): k.strip().strip("[]") for k in measures}
    still_skipped: list[dict] = []
    for s in skipped:
        if s["taxonomy"] != "unresolved":
            still_skipped.append(s)
            continue
        ast = context_model["measures"][s["calculation_name"]]["ast"]
        replaced = 0
        for f in list(iter_fields(ast)):
            key = (f.get("name") or "").strip().strip("[]").lower()
            if key in converted_names:
                f.clear()
                f.update({"node": "measure_ref", "name": converted_names[key]})
                replaced += 1
        if not replaced:
            still_skipped.append(s)
            continue
        result = analyze(s["calculation_name"], ast, fact_table)
        if result["kind"] == "measure":
            measures[result["name"]] = result["dax"]
            if result["table"]:
                measure_table_map[result["name"]] = result["table"]
        else:
            still_skipped.append({"calculation_name": s["calculation_name"],
                                  "reason": result["reason"], "taxonomy": result["taxonomy"]})
    skipped = still_skipped

    output = {
        "measures": measures,
        "measure_table_map": measure_table_map,
        "calculated_columns": columns,
        "parameters": parameters,
        "skipped_measures": skipped,
    }
    with open(data_dir / "converted_dax_measures.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)

    log.info(
        "DAX rewrite: %d measures, %d columns, %d parameters, %d skipped",
        len(measures), len(columns), len(parameters), len(skipped),
    )
    return output
