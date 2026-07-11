"""Classify measures by convertibility using their parsed AST (not substrings).

The previous implementation matched substrings anywhere in the formula, which
mislabelled large formatting/table-calc expressions as "simple aggregation".
Classification here is driven purely by the AST built upstream.
"""

import json
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

# Map AST unsupported-reasons to a human-facing category + note.
_REASON_CATEGORY = {
    "lod_expression": ("lod_expression", "LOD expression — requires semantic rewrite"),
    "table_calculation": ("table_calculation", "table/window calculation — no direct DAX equivalent"),
    "conditional_logic": ("requires_redesign", "conditional logic not yet transpiled"),
    "complex_aggregation": ("requires_redesign", "aggregation shape not yet transpiled"),
    "empty_formula": ("empty", "empty formula"),
    "unsupported_expression": ("unsupported", "manual review required"),
    "unresolved_table_context": ("unresolved", "no reliable table context"),
}


def classify_measure(measure: dict) -> tuple[str, str]:
    """Return ``(classification, note)`` for one measure's AST."""
    ast = measure["ast"]
    node = ast.get("node")
    if node == "single":
        return "simple_aggregation", "directly convertible"
    if node == "binary":
        return "algebraic_aggregation", "directly convertible"
    return _REASON_CATEGORY.get(
        ast.get("reason", "unsupported_expression"),
        ("unsupported", "manual review required"),
    )


def run(semantic_model: dict, data_dir: Path) -> list[dict]:
    """Classify all measures and write ``calculation_classification.json``."""
    classified = []
    for name, measure in semantic_model["measures"].items():
        classification, note = classify_measure(measure)
        classified.append(
            {
                "calculation_name": name,
                "formula": measure.get("formula", ""),
                "classification": classification,
                "note": note,
            }
        )
    with open(data_dir / "calculation_classification.json", "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=4)

    counts: dict[str, int] = {}
    for c in classified:
        counts[c["classification"]] = counts.get(c["classification"], 0) + 1
    log.info("Classified %d measures: %s", len(classified), counts)
    return classified
