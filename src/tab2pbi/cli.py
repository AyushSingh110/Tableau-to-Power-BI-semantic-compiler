"""Command-line interface: ``tab2pbi run <workbook.twbx>``."""

import argparse
import logging
import sys
from pathlib import Path

from . import __version__, pipeline
from .logging_config import configure

DEFAULT_TWBX = Path("examples/Superstore.twbx")
DEFAULT_DATA_DIR = Path("data")


def _summary(result: pipeline.PipelineResult) -> str:
    report = result.report
    lines = [
        "",
        "=" * 60,
        f" tab2pbi summary — {result.twbx_path.name}",
        "=" * 60,
        f" Tables:              {len(result.tables)}",
        f" Calculations total:  {report.get('total_calculations', 0)}",
        f"   measures:          {report.get('measures_converted', 0)}",
        f"   calc columns:      {report.get('columns_converted', 0)}",
        f"   parameters:        {report.get('parameters_converted', 0)}",
        f"   skipped:           {report.get('skipped_count', 0)}",
        f" Coverage:            {report.get('coverage_pct', 0)}%",
        f" Relationships:       {len(result.final_model.get('relationships', []))}",
    ]

    fact = report.get("fact_table_inference", {})
    if fact:
        lines.append(f" Fact table:        {fact.get('table')} ({fact.get('method')})")

    taxonomy = {k: v for k, v in report.get("failure_taxonomy", {}).items() if v}
    if taxonomy:
        lines.append(" Failure taxonomy:")
        for k, v in sorted(taxonomy.items(), key=lambda kv: -kv[1]):
            lines.append(f"   {k:<24} {v}")

    skipped = report.get("skipped_measures", [])
    if skipped:
        lines.append(" Skipped (with reason):")
        for s in skipped:
            lines.append(f"   - {s['calculation_name']}: {s['reason']}")

    lines.append("=" * 60)
    lines.append(f" Artifacts written to: {result.data_dir}")
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tab2pbi",
        description="Deterministic Tableau → Power BI semantic compiler.",
    )
    parser.add_argument("--version", action="version", version=f"tab2pbi {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Compile a .twbx into a Power BI TOM model.")
    run_p.add_argument("twbx", nargs="?", type=Path, default=DEFAULT_TWBX,
                       help=f"Path to the .twbx workbook (default: {DEFAULT_TWBX})")
    run_p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                       help=f"Output directory for artifacts (default: {DEFAULT_DATA_DIR})")
    run_p.add_argument("--extract-dir", type=Path, default=None,
                       help="Directory for the unzipped workbook (default: <data-dir>/twbx_extracted)")
    run_p.add_argument("--fact-table", default=None,
                       help="Override the fact table (physical table name) instead of inferring by size.")
    run_p.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure(logging.DEBUG if getattr(args, "verbose", False) else logging.INFO)

    if args.command == "run":
        if not args.twbx.exists():
            parser.error(f"workbook not found: {args.twbx}")
        result = pipeline.run(
            twbx_path=args.twbx,
            data_dir=args.data_dir,
            extract_dir=args.extract_dir,
            fact_table=args.fact_table,
        )
        print(_summary(result))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
