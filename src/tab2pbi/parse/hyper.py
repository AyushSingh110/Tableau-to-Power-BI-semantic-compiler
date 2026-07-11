"""Read the .hyper extract: schema plus a per-table data sample.

Uses only the official Tableau Hyper API. Every physical table is exported to
its own CSV under ``data_dir/tables`` so that downstream relationship
inference has real, per-table evidence (the legacy single-table CSV silently
prevented cross-table inference).
"""

import json
import re
from pathlib import Path

import pandas as pd
from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    TableName,
    Telemetry,
)

from ..logging_config import get_logger

log = get_logger(__name__)


def _open(hyper_path: Path):
    hyper = HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU)
    connection = Connection(
        endpoint=hyper.endpoint,
        database=str(hyper_path),
        create_mode=CreateMode.NONE,
    )
    return hyper, connection


def _extract_schema(connection) -> list[dict]:
    schema_info = []
    for schema in connection.catalog.get_schema_names():
        for table in connection.catalog.get_table_names(schema):
            table_def = connection.catalog.get_table_definition(table)
            columns = [
                {"column_name": col.name.unescaped, "data_type": str(col.type)}
                for col in table_def.columns
            ]
            schema_info.append(
                {
                    "schema": schema.name.unescaped,
                    "table": table.name.unescaped,
                    "columns": columns,
                }
            )
    return schema_info


def _table_to_df(connection, schema_name: str, table_name: str) -> pd.DataFrame:
    table = TableName(schema_name, table_name)
    columns = [
        col.name.unescaped
        for col in connection.catalog.get_table_definition(table).columns
    ]
    rows = [list(row) for row in connection.execute_query(f"SELECT * FROM {table}")]
    return pd.DataFrame(rows, columns=columns)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def run(hyper_path: Path, data_dir: Path) -> dict:
    """Extract schema and per-table samples from the Hyper extract."""
    data_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = data_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    hyper, conn = _open(hyper_path)
    try:
        schema = _extract_schema(conn)
        with open(data_dir / "parsed_hyper_schema.json", "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=4)

        exported = {}
        for entry in schema:
            df = _table_to_df(conn, entry["schema"], entry["table"])
            csv_path = tables_dir / f"{_safe_name(entry['table'])}.csv"
            df.to_csv(csv_path, index=False)
            exported[entry["table"]] = csv_path
            log.info(
                "Exported table %s (%d rows, %d cols)",
                entry["table"],
                len(df),
                len(df.columns),
            )

        # Backwards-compatible single-file sample of the widest table.
        if schema:
            widest = max(schema, key=lambda e: len(e["columns"]))
            sample = pd.read_csv(exported[widest["table"]])
            sample.to_csv(data_dir / "hyper_raw_data.csv", index=False)
    finally:
        conn.close()
        hyper.close()

    total_cols = sum(len(t["columns"]) for t in schema)
    log.info("Hyper schema: %d tables, %d columns", len(schema), total_cols)
    return {"schema": schema, "tables_dir": tables_dir}
