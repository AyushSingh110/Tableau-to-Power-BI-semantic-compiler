#!/usr/bin/env python
"""Single-entry orchestrator for the Tableau → Power BI pipeline.

Thin wrapper around the ``tab2pbi`` package so the pipeline can be run without
installing the console script:

    python run_pipeline.py --twbx examples/Superstore.twbx

All stages run in order and write their artifacts under ``--data-dir``.
"""

import argparse
import logging
import sys
from pathlib import Path

# Allow running from a source checkout without installation.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tab2pbi import pipeline  # noqa: E402
from tab2pbi.cli import _summary  # noqa: E402
from tab2pbi.logging_config import configure  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the full tab2pbi pipeline.")
    parser.add_argument("--twbx", type=Path, default=Path("examples/Superstore.twbx"),
                        help="Path to the .twbx workbook.")
    parser.add_argument("--data-dir", type=Path, default=Path("data"),
                        help="Output directory for artifacts.")
    parser.add_argument("--extract-dir", type=Path, default=None,
                        help="Directory for the unzipped workbook.")
    parser.add_argument("--fact-table", default=None,
                        help="Override the fact table instead of inferring by size.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args(argv)

    configure(logging.DEBUG if args.verbose else logging.INFO)
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


if __name__ == "__main__":
    sys.exit(main())
