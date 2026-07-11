"""Helpers for walking the typed AST produced by the parser."""

from __future__ import annotations

from collections.abc import Iterator


def children(node: dict) -> list[dict]:
    """Return the direct child AST nodes of ``node``."""
    kind = node.get("node")
    if kind == "aggregation":
        return [node["arg"]]
    if kind == "function":
        return list(node.get("args", []))
    if kind in ("binary", "comparison", "logical"):
        return [node["left"], node["right"]]
    if kind in ("unary", "not"):
        return [node["operand"]]
    if kind == "conditional":
        out = []
        for br in node["branches"]:
            out.extend([br["when"], br["then"]])
        if node.get("otherwise") is not None:
            out.append(node["otherwise"])
        return out
    return []


def walk(node: dict) -> Iterator[dict]:
    """Yield ``node`` and every descendant (pre-order)."""
    yield node
    for c in children(node):
        yield from walk(c)


def iter_fields(node: dict) -> Iterator[dict]:
    """Yield every ``field`` node in the tree."""
    for n in walk(node):
        if n.get("node") == "field":
            yield n


def has_aggregation(node: dict) -> bool:
    """True if the tree contains any aggregation node."""
    return any(n.get("node") == "aggregation" for n in walk(node))


def has_field(node: dict) -> bool:
    """True if the tree references any field."""
    return any(n.get("node") == "field" for n in walk(node))


def field_tables(node: dict) -> set[str]:
    """Set of resolved owning tables across all field nodes (skips unresolved)."""
    return {f["table"] for f in iter_fields(node) if f.get("table")}
