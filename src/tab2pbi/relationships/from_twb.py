"""Extract relationships declared in the Tableau workbook XML.

Detects Tableau's modern logical relationships and legacy physical joins.
Join keys that Tableau defers to query time are preserved as such rather than
guessed.
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

_JOIN_RE = re.compile(r"\[([^\]]+)\]\.\[([^\]]+)\]\s*=\s*\[([^\]]+)\]\.\[([^\]]+)\]")


def extract_physical_joins(root: ET.Element) -> list[dict]:
    joins = []
    for rel in root.findall(".//relation[@type='join']"):
        clause = rel.find("clause")
        expr = clause.attrib.get("expression") if clause is not None else None
        if not expr:
            continue
        match = _JOIN_RE.search(expr)
        if not match:
            continue
        lt, lc, rt, rc = match.groups()
        joins.append(
            {
                "from_table": lt,
                "from_column": lc,
                "to_table": rt,
                "to_column": rc,
                "join_type": rel.attrib.get("join", "inner"),
                "mode": "physical_join",
                "expression": expr,
            }
        )
    return joins


def extract_logical_relationships(root: ET.Element) -> list[dict]:
    relationships = []
    for rel in root.findall(".//relationship"):
        columns = rel.findall(".//column")
        for col in columns:
            relationships.append(
                {
                    "from_table": rel.attrib.get("from-table"),
                    "from_column": col.attrib.get("from"),
                    "to_table": rel.attrib.get("to-table"),
                    "to_column": col.attrib.get("to"),
                    "mode": "logical_relationship",
                    "raw_attributes": dict(rel.attrib),
                }
            )
        if not columns:
            relationships.append(
                {
                    "mode": "logical_relationship_raw",
                    "raw_attributes": dict(rel.attrib),
                    "note": "Tableau logical relationship — join keys resolved at query time",
                    "confidence": "engine-resolved",
                }
            )
    return relationships


def run(twb_path: Path, data_dir: Path) -> list[dict]:
    root = ET.parse(twb_path).getroot()
    has_physical = bool(root.findall(".//relation[@type='join']"))
    has_logical = bool(root.findall(".//relationship"))

    if has_logical:
        relationships = extract_logical_relationships(root)
        mode = "logical"
    elif has_physical:
        relationships = extract_physical_joins(root)
        mode = "physical"
    else:
        relationships = []
        mode = "none"

    with open(data_dir / "relationships_from_twb.json", "w", encoding="utf-8") as f:
        json.dump(relationships, f, indent=4)
    log.info("TWB relationships: %d records (mode=%s)", len(relationships), mode)
    return relationships
