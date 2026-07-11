"""Pratt parser for the Tableau calculation language.

Turns a token stream into a typed AST (plain JSON-serializable dicts). The
grammar covered: literals, field references, function/aggregation calls,
arithmetic/string/comparison/logical operators, and IF/CASE conditionals. LOD
expressions (``{ FIXED ... }``) are recognised and returned as ``unsupported``
nodes with a reason.

Anything the parser cannot handle raises ``ParseError``; the public
:func:`build_ast` wrapper converts that into a ``parse_error`` AST node so the
pipeline never crashes and never silently drops a calculation.
"""

from __future__ import annotations

from .tokenizer import TokenizeError, tokenize

# Aggregation function names (single-argument aggregate of a field/expression).
AGG_FUNCS = {
    "SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD",
    "MEDIAN", "ATTR", "STDEV", "STDEVP", "VAR", "VARP",
}

# Infix operator binding powers (higher binds tighter).
_INFIX_BP = {
    "OR": 1, "AND": 2,
    "=": 3, "==": 3, "<>": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3,
    "+": 4, "-": 4,
    "*": 5, "/": 5, "%": 5,
    "^": 6,
}
_COMPARISONS = {"=", "==", "<>", "!=", "<", ">", "<=", ">="}


class ParseError(ValueError):
    """Raised for input the parser cannot turn into a supported AST."""


class _Parser:
    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def next(self):
        t = self.toks[self.i]
        self.i += 1
        return t

    def expect(self, kind, value=None):
        t = self.peek()
        if t.kind != kind or (value is not None and t.value != value):
            raise ParseError(f"expected {value or kind}, got {t.value!r}")
        return self.next()

    # -- expression precedence climbing --
    def parse_expression(self, min_bp=0):
        left = self.parse_prefix()
        while True:
            t = self.peek()
            op = self._infix_op(t)
            if op is None:
                break
            bp = _INFIX_BP[op]
            if bp <= min_bp:
                break
            self.next()
            right_bp = bp - 1 if op == "^" else bp
            right = self.parse_expression(right_bp)
            left = self._make_infix(op, left, right)
        return left

    def _infix_op(self, t):
        if t.kind == "OP" and t.value in _INFIX_BP:
            return t.value
        if t.kind == "KW" and t.value in ("AND", "OR"):
            return t.value
        return None

    def _make_infix(self, op, left, right):
        if op in ("AND", "OR"):
            return {"node": "logical", "op": op, "left": left, "right": right}
        if op in _COMPARISONS:
            norm = {"==": "=", "!=": "<>"}.get(op, op)
            return {"node": "comparison", "op": norm, "left": left, "right": right}
        return {"node": "binary", "op": op, "left": left, "right": right}

    # -- prefix / primary --
    def parse_prefix(self):
        t = self.peek()

        if t.kind == "OP" and t.value == "-":
            self.next()
            return {"node": "unary", "op": "-", "operand": self.parse_expression(5)}
        if t.kind == "OP" and t.value == "+":
            self.next()
            return self.parse_expression(5)
        if t.kind == "KW" and t.value == "NOT":
            self.next()
            return {"node": "not", "operand": self.parse_expression(2)}
        return self.parse_primary()

    def parse_primary(self):
        t = self.next()

        if t.kind == "NUMBER":
            val = float(t.value) if "." in t.value else int(t.value)
            return {"node": "constant", "dtype": "number", "value": val}
        if t.kind == "STRING":
            return {"node": "constant", "dtype": "string", "value": t.value}
        if t.kind == "KW" and t.value in ("TRUE", "FALSE"):
            return {"node": "constant", "dtype": "boolean", "value": t.value == "TRUE"}
        if t.kind == "KW" and t.value == "NULL":
            return {"node": "constant", "dtype": "null", "value": None}
        if t.kind == "FIELD":
            return {"node": "field", "name": t.value}
        if t.kind == "OP" and t.value == "(":
            expr = self.parse_expression(0)
            self.expect("OP", ")")
            return expr
        if t.kind == "KW" and t.value == "IF":
            return self.parse_if()
        if t.kind == "KW" and t.value == "CASE":
            return self.parse_case()
        if t.kind == "LBrace":
            return self.consume_lod()
        if t.kind == "IDENT":
            return self.parse_call(t.value)

        raise ParseError(f"unexpected token {t.value!r}")

    def parse_call(self, name):
        if not (self.peek().kind == "OP" and self.peek().value == "("):
            raise ParseError(f"bare identifier {name!r}")
        self.expect("OP", "(")
        args = []
        if not (self.peek().kind == "OP" and self.peek().value == ")"):
            args.append(self.parse_expression(0))
            while self.peek().kind == "OP" and self.peek().value == ",":
                self.next()
                args.append(self.parse_expression(0))
        self.expect("OP", ")")

        upper = name.upper()
        if upper in AGG_FUNCS and len(args) == 1:
            return {"node": "aggregation", "agg": upper, "arg": args[0]}
        return {"node": "function", "name": upper, "args": args}

    def parse_if(self):
        branches = []
        cond = self.parse_expression(0)
        self.expect("KW", "THEN")
        then = self.parse_expression(0)
        branches.append({"when": cond, "then": then})
        while self.peek().kind == "KW" and self.peek().value == "ELSEIF":
            self.next()
            c = self.parse_expression(0)
            self.expect("KW", "THEN")
            branches.append({"when": c, "then": self.parse_expression(0)})
        otherwise = None
        if self.peek().kind == "KW" and self.peek().value == "ELSE":
            self.next()
            otherwise = self.parse_expression(0)
        self.expect("KW", "END")
        return {"node": "conditional", "branches": branches, "otherwise": otherwise}

    def parse_case(self):
        subject = self.parse_expression(0)
        branches = []
        while self.peek().kind == "KW" and self.peek().value == "WHEN":
            self.next()
            val = self.parse_expression(0)
            self.expect("KW", "THEN")
            result = self.parse_expression(0)
            branches.append(
                {
                    "when": {"node": "comparison", "op": "=", "left": subject, "right": val},
                    "then": result,
                }
            )
        otherwise = None
        if self.peek().kind == "KW" and self.peek().value == "ELSE":
            self.next()
            otherwise = self.parse_expression(0)
        self.expect("KW", "END")
        return {"node": "conditional", "branches": branches, "otherwise": otherwise}

    def consume_lod(self):
        # Consume a balanced { ... } LOD block; we do not model it.
        depth = 1
        while depth:
            t = self.next()
            if t.kind == "LBrace":
                depth += 1
            elif t.kind == "RBrace":
                depth -= 1
            elif t.kind == "EOF":
                raise ParseError("unterminated LOD expression")
        return {"node": "unsupported", "reason": "lod_expression"}


def parse(formula: str) -> dict:
    """Parse a formula into an AST, raising ParseError on failure."""
    tokens = tokenize(formula)
    p = _Parser(tokens)
    ast = p.parse_expression(0)
    if p.peek().kind != "EOF":
        raise ParseError(f"trailing tokens from {p.peek().value!r}")
    return ast


def build_ast(formula: str) -> dict:
    """Public entry point: never raises; returns a node with a reason on failure."""
    raw = formula or ""
    if not raw.strip():
        return {"node": "unsupported", "reason": "empty_formula", "formula": raw}
    try:
        ast = parse(raw)
    except (ParseError, TokenizeError) as exc:
        return {"node": "parse_error", "reason": str(exc), "formula": raw}
    # Preserve the original formula on unsupported nodes for auditing.
    if ast.get("node") == "unsupported":
        ast.setdefault("formula", raw)
    return ast
