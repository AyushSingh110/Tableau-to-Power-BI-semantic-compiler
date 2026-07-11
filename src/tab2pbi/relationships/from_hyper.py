"""Infer foreign-key relationships from actual per-table data.

The legacy version read a single wide CSV whose columns had no ``table.column``
prefixes, so its table split was always empty and it silently emitted zero
relationships. This version profiles each physical table's own CSV, detects
primary keys (unique + non-null) and foreign keys (referential coverage above a
threshold), and reports low-coverage candidates as unresolved rather than
dropping them.
"""

import json
from pathlib import Path

import pandas as pd

from ..logging_config import get_logger
from ..parse.hyper import _safe_name

log = get_logger(__name__)

COVERAGE_THRESHOLD = 0.95


def _load_tables(hyper_schema: list[dict], tables_dir: Path) -> dict[str, pd.DataFrame]:
    frames = {}
    for entry in hyper_schema:
        csv_path = tables_dir / f"{_safe_name(entry['table'])}.csv"
        if csv_path.exists():
            frames[entry["table"]] = pd.read_csv(csv_path)
    return frames


def _profile(frames: dict[str, pd.DataFrame]) -> dict[str, dict]:
    stats = {}
    for table, df in frames.items():
        stats[table] = {
            col: {
                "row_count": len(df),
                "distinct_count": int(df[col].nunique(dropna=True)),
                "null_count": int(df[col].isna().sum()),
                "dtype": str(df[col].dtype),
            }
            for col in df.columns
        }
    return stats


def _primary_keys(stats: dict[str, dict]) -> dict[str, list[str]]:
    pks: dict[str, list[str]] = {}
    for table, cols in stats.items():
        pks[table] = [
            col
            for col, s in cols.items()
            if s["row_count"] > 0
            and s["distinct_count"] == s["row_count"]
            and s["null_count"] == 0
        ]
    return pks


def run(hyper_schema: list[dict], tables_dir: Path, data_dir: Path) -> dict:
    frames = _load_tables(hyper_schema, tables_dir)
    stats = _profile(frames)
    primary_keys = _primary_keys(stats)

    relationships = []
    unresolved = []

    for fact_table, fact_cols in stats.items():
        for dim_table, dim_pks in primary_keys.items():
            if fact_table == dim_table:
                continue
            for fk_col in fact_cols:
                for pk_col in dim_pks:
                    if stats[dim_table][pk_col]["dtype"] != fact_cols[fk_col]["dtype"]:
                        continue
                    fk_vals = set(frames[fact_table][fk_col].dropna().unique())
                    if not fk_vals:
                        continue
                    pk_vals = set(frames[dim_table][pk_col].dropna().unique())
                    coverage = len(fk_vals & pk_vals) / len(fk_vals)
                    if coverage >= COVERAGE_THRESHOLD:
                        relationships.append(
                            {
                                "from_table": fact_table,
                                "from_column": fk_col,
                                "to_table": dim_table,
                                "to_column": pk_col,
                                "cardinality": "ManyToOne",
                                "cross_filter_direction": "Single",
                                "confidence": round(coverage, 3),
                                "evidence": {"fk_coverage": round(coverage, 3), "pk_verified": True},
                            }
                        )
                    elif coverage > 0.5:
                        unresolved.append(
                            {
                                "from_table": fact_table,
                                "from_column": fk_col,
                                "to_table": dim_table,
                                "to_column": pk_col,
                                "coverage": round(coverage, 3),
                                "reason": f"coverage {coverage:.3f} below threshold {COVERAGE_THRESHOLD}",
                            }
                        )

    output = {"relationships": relationships, "unresolved_relationships": unresolved}
    with open(data_dir / "inferred_powerbi_relationships.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4)
    log.info(
        "Inferred relationships: %d confident, %d unresolved",
        len(relationships),
        len(unresolved),
    )
    return output
