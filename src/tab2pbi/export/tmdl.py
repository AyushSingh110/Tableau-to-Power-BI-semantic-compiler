"""TMDL semantic-model emitter (canonical model -> a *.SemanticModel/ folder).

Additive: the existing TOM/Model.json export is untouched. Structure is grounded
in the reference SemanticModel at
``experiments/visual-spike/pbir_reference/Superstore.SemanticModel`` for data
columns, partitions, relationships, and the model/database/culture scaffolding.

⚠️ The one part NOT grounded in the reference (it has no measures) is the
**measure / calculated-column** TMDL syntax; that follows the official TMDL spec
(learn.microsoft.com/analysis-services/tmdl). Per the V2 render-risk guard we
emit only the minimal valid properties (name, expression, formatString/dataType,
lineageTag, summarizeBy) — no optional properties we can't verify.

Data source: one CSV **import partition** per table, sourcing the per-table CSVs
the pipeline already generates (``data/tables/*.csv``). The M ``File.Contents``
path is ABSOLUTE (as Power BI itself emits) so the .pbip opens without hand
editing — moving the repo breaks the path; re-run the pipeline to regenerate.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

from ..logging_config import get_logger

log = get_logger(__name__)

# Fixed namespace for deterministic lineageTag GUIDs (uuid5).
_NS = uuid.UUID("2b7c1e00-0000-4000-8000-abcdef012345")
COMPATIBILITY_LEVEL = 1550

# Hyper data_type -> (TMDL dataType, M type, summarizeBy)
_TYPE_MAP = {
    "TEXT": ("string", "type text", "none"),
    "DOUBLE": ("double", "type number", "sum"),
    "FLOAT": ("double", "type number", "sum"),
    "NUMERIC": ("double", "type number", "sum"),
    "BIG_INT": ("int64", "Int64.Type", "sum"),
    "INT": ("int64", "Int64.Type", "sum"),
    "SMALL_INT": ("int64", "Int64.Type", "sum"),
    "DATE": ("dateTime", "type date", "none"),
    "TIMESTAMP": ("dateTime", "type datetime", "none"),
    "BOOL": ("boolean", "type logical", "none"),
}


def _types_for(raw: str) -> tuple[str, str, str]:
    key = raw.upper().strip()
    return _TYPE_MAP.get(key, ("string", "type text", "none"))


def _esc(name: str) -> str:
    """Single-quote a TMDL object name/reference if it needs it."""
    if re.fullmatch(r"[A-Za-z0-9_]+", name):
        return name
    return "'" + name.replace("'", "''") + "'"


def _strip_brackets(name: str) -> str:
    return name.strip().lstrip("[").rstrip("]")


def _guid(*parts: str) -> str:
    return str(uuid.uuid5(_NS, "::".join(parts)))


def _m_source(csv_path: Path, columns: list[dict]) -> str:
    transforms = ", ".join(
        f'{{"{c["column_name"]}", {_types_for(c["data_type"])[1]}}}' for c in columns
    )
    # Power Query M treats backslash as a literal character, not an escape.
    # Emit the raw OS path with single backslashes, exactly as Power BI itself
    # writes it in its reference TMDL. Escaping to "\\" produces an invalid path
    # and the import partition silently loads nothing.
    p = str(csv_path)
    return (
        "\t\tsource =\n"
        "\t\t\t\tlet\n"
        f'\t\t\t\t    Source = Csv.Document(File.Contents("{p}"),'
        f'[Delimiter=",", Columns={len(columns)}, Encoding=65001, QuoteStyle=QuoteStyle.None]),\n'
        "\t\t\t\t    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),\n"
        f"\t\t\t\t    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\",{{{transforms}}})\n"
        "\t\t\t\tin\n"
        "\t\t\t\t    #\"Changed Type\""
    )


def _is_single_line(expr: str) -> bool:
    return "\n" not in expr and "\r" not in expr


def emit_table(entry: dict, final_model: dict, csv_path: Path, skips: list) -> str:
    """Emit one table's TMDL. Multi-line DAX expressions are skipped (and
    appended to ``skips``) rather than emitted as invalid single-line TMDL."""
    table = entry["table"]
    columns = entry["columns"]
    lines = [f"table {_esc(table)}", f"\tlineageTag: {_guid('table', table)}", ""]

    # data columns
    for col in columns:
        dtype, _m, summ = _types_for(col["data_type"])
        cname = col["column_name"]
        lines += [
            f"\tcolumn {_esc(cname)}",
            f"\t\tdataType: {dtype}",
            f"\t\tlineageTag: {_guid('col', table, cname)}",
            f"\t\tsummarizeBy: {summ}",
            f"\t\tsourceColumn: {cname}",
            "",
        ]

    # calculated columns owned by this table (row-level, e.g. DATEDIFF)
    for c in final_model.get("calculated_columns", []):
        if c["table"] != table:
            continue
        name = _strip_brackets(c["name"])
        if not _is_single_line(c["dax"]):
            skips.append({"name": name, "kind": "calc_column", "reason": "multi-line DAX not emitted as TMDL"})
            continue
        lines += [
            f"\tcolumn {_esc(name)} = {c['dax']}",
            "\t\tdataType: int64",
            f"\t\tlineageTag: {_guid('calccol', table, name)}",
            "\t\tsummarizeBy: none",
            "",
        ]

    # parameters (constant calcs) -> constant calc columns, honestly annotated
    for p in final_model.get("parameters", []):
        if p.get("table") != table:
            continue
        name = _strip_brackets(p["name"])
        if not _is_single_line(p["dax"]):
            skips.append({"name": name, "kind": "parameter", "reason": "multi-line DAX not emitted as TMDL"})
            continue
        dtype = "int64" if re.fullmatch(r"-?\d+", p["dax"].strip()) else "string"
        lines += [
            f"\tcolumn {_esc(name)} = {p['dax']}",
            f"\t\tdataType: {dtype}",
            f"\t\tlineageTag: {_guid('param', table, name)}",
            "\t\tsummarizeBy: none",
            f'\t\tannotation Tab2PBI_Origin = "{p["note"]}"',
            "",
        ]

    # measures owned by this table (minimal valid TMDL — render-risk guard)
    mtm = final_model.get("measure_table_map", {})
    for mname, dax in final_model.get("measures", {}).items():
        if mtm.get(mname) != table:
            continue
        name = _strip_brackets(mname)
        if not _is_single_line(dax):
            skips.append({"name": name, "kind": "measure", "reason": "multi-line DAX not emitted as TMDL"})
            continue
        lines += [
            f"\tmeasure {_esc(name)} = {dax}",
            "\t\tformatString: General",
            f"\t\tlineageTag: {_guid('measure', table, name)}",
            "",
        ]

    # import partition
    lines += [
        f"\tpartition {_esc(table)} = m",
        "\t\tmode: import",
        _m_source(csv_path, columns),
        "",
        "\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def emit_model(table_names: list[str]) -> str:
    refs = "\n".join(f"ref table {_esc(t)}" for t in table_names)
    query_order = ", ".join(f'"{t}"' for t in table_names)
    return (
        "model Model\n"
        "\tculture: en-US\n"
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
        "\tdataAccessOptions\n"
        "\t\tlegacyRedirects\n"
        "\t\treturnErrorValuesAsNull\n"
        "\n"
        "annotation __PBI_TimeIntelligenceEnabled = 0\n"
        "\n"
        f"annotation PBI_QueryOrder = [{query_order}]\n"
        "\n"
        f"{refs}\n"
        "\n"
        "ref cultureInfo en-US\n"
    )


def emit_relationships(inferred: dict) -> str:
    blocks = []
    for rel in inferred.get("relationships", []):
        rid = _guid("rel", rel["from_table"], rel["from_column"], rel["to_table"], rel["to_column"])
        blocks.append(
            f"relationship {rid}\n"
            f"\tfromColumn: {_esc(rel['from_table'])}.{_esc(rel['from_column'])}\n"
            f"\ttoColumn: {_esc(rel['to_table'])}.{_esc(rel['to_column'])}\n"
        )
    return "\n".join(blocks)


DATABASE_TMDL = f"database\n\tcompatibilityLevel: {COMPATIBILITY_LEVEL}\n"
PBISM = '{\n  "version": "4.2",\n  "settings": {}\n}'
CULTURE_TMDL = (
    "cultureInfo en-US\n\n"
    "\tlinguisticMetadata =\n"
    "\t\t\t{\n"
    '\t\t\t  "Version": "1.0.0",\n'
    '\t\t\t  "Language": "en-US"\n'
    "\t\t\t}\n"
    "\t\tcontentType: json\n"
)


def run(hyper_schema: list[dict], final_model: dict, inferred: dict,
        out_semantic_dir: Path, csv_dir: Path) -> dict:
    """Emit the *.SemanticModel/ folder. Returns a small info dict."""
    out = Path(out_semantic_dir)
    definition = out / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    (definition / "cultures").mkdir(parents=True, exist_ok=True)

    (out / "definition.pbism").write_text(PBISM, encoding="utf-8")
    (definition / "database.tmdl").write_text(DATABASE_TMDL, encoding="utf-8")
    (definition / "cultures" / "en-US.tmdl").write_text(CULTURE_TMDL, encoding="utf-8")

    table_names = [e["table"] for e in hyper_schema]
    (definition / "model.tmdl").write_text(emit_model(table_names), encoding="utf-8")

    rel_text = emit_relationships(inferred)
    if rel_text.strip():
        (definition / "relationships.tmdl").write_text(rel_text, encoding="utf-8")

    def safe(t: str) -> str:  # matches parse/hyper CSV naming
        return re.sub(r"[^A-Za-z0-9_.-]", "_", t)

    skips: list[dict] = []
    for entry in hyper_schema:
        csv_path = (Path(csv_dir) / f"{safe(entry['table'])}.csv").resolve()
        (definition / "tables" / f"{safe(entry['table'])}.tmdl").write_text(
            emit_table(entry, final_model, csv_path, skips), encoding="utf-8"
        )

    mtm = final_model.get("measure_table_map", {})
    skipped_names = {s["name"] for s in skips}
    measures_emitted = sum(
        1 for m in final_model.get("measures", {})
        if mtm.get(m) and _strip_brackets(m) not in skipped_names
    )
    cols_emitted = sum(
        1 for c in final_model.get("calculated_columns", [])
        if _strip_brackets(c["name"]) not in skipped_names
    )
    params_emitted = sum(
        1 for p in final_model.get("parameters", [])
        if _strip_brackets(p["name"]) not in skipped_names
    )

    log.info(
        "TMDL model: %d tables, %d measures, %d calc columns, %d params, %d relationships, %d skipped (multi-line) -> %s",
        len(table_names), measures_emitted, cols_emitted, params_emitted,
        len(inferred.get("relationships", [])), len(skips), out,
    )
    return {
        "semantic_dir": str(out),
        "tables": len(table_names),
        "measures": measures_emitted,
        "calculated_columns": cols_emitted,
        "parameters": params_emitted,
        "relationships": len(inferred.get("relationships", [])),
        "skipped_multiline": skips,
    }
