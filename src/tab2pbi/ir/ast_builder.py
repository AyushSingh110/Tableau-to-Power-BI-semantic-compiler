"""Build a small, honest AST for each Tableau calculated field.

Phase 1 uses conservative regular-expression recognition. Only two shapes are
recognised as convertible:

- ``single`` : a single aggregation of one field, e.g. ``SUM([Sales])``.
- ``binary`` : an algebraic combination of two aggregations, e.g.
  ``SUM([Profit]) / SUM([Sales])``.

Everything else becomes an ``unsupported`` node **with a reason** — never a
silent drop and never a fabricated translation. Phase 2 replaces this with a
real tokenizer/parser.
"""

import re

AGG_FUNCS = ("SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD")
_AGG = "|".join(AGG_FUNCS)

_SINGLE_RE = re.compile(
    rf"^\s*(?P<agg>{_AGG})\s*\(\s*\[(?P<field>[^\]]+)\]\s*\)\s*$",
    re.IGNORECASE,
)
_BINARY_RE = re.compile(
    rf"^\s*(?P<lagg>{_AGG})\s*\(\s*\[(?P<lfield>[^\]]+)\]\s*\)\s*"
    r"(?P<op>[-+*/])\s*"
    rf"(?P<ragg>{_AGG})\s*\(\s*\[(?P<rfield>[^\]]+)\]\s*\)\s*$",
    re.IGNORECASE,
)

_LINE_COMMENT_RE = re.compile(r"//[^\r\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(formula: str) -> str:
    """Remove Tableau ``//`` and ``/* */`` comments."""
    without_block = _BLOCK_COMMENT_RE.sub(" ", formula)
    return _LINE_COMMENT_RE.sub(" ", without_block)


def _unsupported_reason(text: str) -> str:
    """Classify why an expression is not convertible, from its structure."""
    upper = text.upper()
    if re.search(r"\{\s*(FIXED|INCLUDE|EXCLUDE)", upper) or re.search(
        r"\b(FIXED|INCLUDE|EXCLUDE)\b", upper
    ):
        return "lod_expression"
    if re.search(
        r"\b(WINDOW_\w+|RUNNING_\w+|LOOKUP|INDEX|FIRST|LAST|TOTAL|RANK\w*|"
        r"PREVIOUS_VALUE|SIZE)\s*\(",
        upper,
    ):
        return "table_calculation"
    if re.search(r"\b(IF|CASE|WHEN|ELSEIF|THEN)\b", upper):
        return "conditional_logic"
    if re.search(rf"\b({_AGG})\s*\(", upper):
        return "complex_aggregation"
    return "unsupported_expression"


def build_ast(formula: str) -> dict:
    """Return an AST node for ``formula``.

    Convertible shapes yield ``single``/``binary`` nodes; anything else yields
    an ``unsupported`` node carrying a ``reason`` and the original formula.
    """
    raw = formula or ""
    stripped = strip_comments(raw).strip()
    if not stripped:
        return {"node": "unsupported", "reason": "empty_formula", "formula": raw}

    m = _SINGLE_RE.match(stripped)
    if m:
        return {"node": "single", "agg": m.group("agg").upper(), "field": m.group("field")}

    m = _BINARY_RE.match(stripped)
    if m:
        return {
            "node": "binary",
            "op": m.group("op"),
            "left": {"agg": m.group("lagg").upper(), "field": m.group("lfield")},
            "right": {"agg": m.group("ragg").upper(), "field": m.group("rfield")},
        }

    return {
        "node": "unsupported",
        "reason": _unsupported_reason(stripped),
        "formula": raw,
    }
