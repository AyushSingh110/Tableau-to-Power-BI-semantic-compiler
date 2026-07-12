"""CLI for the V1 visual compiler: Tableau worksheets -> PBIR report."""

from __future__ import annotations

import argparse
import csv
import json
import tempfile
import zipfile
from pathlib import Path

from ..logging_config import configure, get_logger
from . import emit_pbir, extract, report

log = get_logger(__name__)

DEFAULT_TWBX = Path("examples/Superstore.twbx")
DEFAULT_COLUMNS = Path("data/hyper_raw_data.csv")


def _twb_from_twbx(twbx: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="visual_"))
    with zipfile.ZipFile(twbx) as z:
        z.extractall(tmp)
    return next(tmp.rglob("*.twb"))


def _columns(path: Path) -> list[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))


def add_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument("--twbx", type=Path, default=DEFAULT_TWBX)
    p.add_argument("--entity", default="hyper_raw_data",
                   help="Semantic-model table the visuals bind to (default: hyper_raw_data).")
    p.add_argument("--columns-from", type=Path, default=DEFAULT_COLUMNS,
                   help="CSV whose header lists the model's columns (for field resolution).")
    p.add_argument("--out", type=Path, default=Path("data/visual_report/Superstore.Report"),
                   help="Output *.Report folder.")
    p.add_argument("--model-path", default="../Superstore.SemanticModel",
                   help="Relative byPath to the paired SemanticModel (for definition.pbir).")
    p.add_argument("--report-json", type=Path, default=None,
                   help="Optional path to also write the visual_conversion_report JSON.")


def run(args: argparse.Namespace) -> int:
    if not args.twbx.exists():
        raise SystemExit(f"workbook not found: {args.twbx}")
    if not args.columns_from.exists():
        raise SystemExit(
            f"columns file not found: {args.columns_from}\n"
            "Run the data pipeline first (produces data/hyper_raw_data.csv) or pass --columns-from."
        )

    columns = _columns(args.columns_from)
    twb = _twb_from_twbx(args.twbx)
    pages = extract.extract_from_twb(twb, args.entity, columns)

    emit_info = emit_pbir.emit(pages, args.out, args.model_path)
    rep = report.build_report(pages)
    rep["emission"] = emit_info

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(rep, indent=2), encoding="utf-8")

    print(report.summary(rep, pages))
    print(f" Report written to:   {emit_info['report_dir']}")
    print(f" Schema validation:   {', '.join(emit_info['schema_validation'])}")
    print(f" Bound entity:        {args.entity}  (paired model: {args.model_path})")
    print(" NOTE: schema-valid != render-verified — open in Power BI Desktop to confirm.\n")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="tab2pbi-visual",
        description="V1 visual compiler: Tableau worksheets -> Power BI PBIR report.",
    )
    add_arguments(parser)
    args = parser.parse_args(argv)
    configure()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
