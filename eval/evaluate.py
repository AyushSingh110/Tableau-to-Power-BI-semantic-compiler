#!/usr/bin/env python
"""Evaluation harness: compare generated measures to Tableau ground truth.

Reports TWO independent numbers (never conflated — see docs/EVALUATION.md):

  * proxy-correctness   : this repo's pandas AST-evaluator vs Tableau values.
                          Validates the parser/IR, NOT the generated DAX.
  * engine-verified     : Power BI / Tabular Editor values (hand-recorded in the
                          ground-truth CSV) vs Tableau values. The real anchor.

Ground-truth CSV columns:
    measure          - calculation name, exactly as in the model (with brackets)
    tableau_value    - value shown in Tableau (the source of truth)
    powerbi_value    - OPTIONAL value read back from Power BI after loading the
                       generated Model.json (leave blank if not hand-checked)

Usage:
    python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tab2pbi.evaluation import NotEvaluable, evaluate  # noqa: E402


def _load_tables(data_dir: Path, schema: list[dict]) -> dict:
    import re
    frames = {}
    for entry in schema:
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", entry["table"])
        csv = data_dir / "tables" / f"{safe}.csv"
        if csv.exists():
            frames[entry["table"]] = pd.read_csv(csv)
    return frames


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="tab2pbi evaluation harness")
    ap.add_argument("--ground-truth", type=Path, required=True)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--tolerance", type=float, default=1e-6,
                    help="relative tolerance for numeric equivalence")
    args = ap.parse_args(argv)

    schema = json.loads((args.data_dir / "parsed_hyper_schema.json").read_text())
    context = json.loads((args.data_dir / "semantic_model_with_context.json").read_text())
    gt = pd.read_csv(args.ground_truth)
    tables = _load_tables(args.data_dir, schema)
    measures = context["measures"]

    def close(a, b):
        return abs(a - b) <= args.tolerance * max(1.0, abs(b))

    rows = []
    proxy_total = proxy_ok = 0
    engine_total = engine_ok = 0

    for _, r in gt.iterrows():
        name = r["measure"]
        tv = float(r["tableau_value"])
        row = {"measure": name, "tableau_value": tv, "proxy": None, "proxy_match": None,
               "powerbi_value": None, "engine_match": None, "status": ""}

        measure = measures.get(name)
        if measure is None:
            row["status"] = "not_in_model"
        else:
            try:
                pv = evaluate(measure["ast"], tables)
                row["proxy"] = pv
                row["proxy_match"] = close(pv, tv)
                proxy_total += 1
                proxy_ok += int(row["proxy_match"])
                row["status"] = "evaluated"
            except NotEvaluable as e:
                row["status"] = f"not_evaluated ({e})"

        pbi = r.get("powerbi_value")
        if pbi is not None and str(pbi).strip() != "" and not pd.isna(pbi):
            ev = float(pbi)
            row["powerbi_value"] = ev
            row["engine_match"] = close(ev, tv)
            engine_total += 1
            engine_ok += int(row["engine_match"])

        rows.append(row)

    print("\n=== tab2pbi evaluation ===")
    for row in rows:
        proxy = f"{row['proxy']:.4f}" if row["proxy"] is not None else "  -  "
        print(f"  {row['measure']:<40} tableau={row['tableau_value']:<12.4f} "
              f"proxy={proxy:<12} match={row['proxy_match']}  [{row['status']}]")

    print("\n  PROXY-correctness (pandas AST vs Tableau) — validates parser, NOT DAX:")
    print(f"    {proxy_ok}/{proxy_total} match"
          + (f"  ({100*proxy_ok/proxy_total:.1f}%)" if proxy_total else "  (n/a)"))
    print("  ENGINE-verified (Power BI vs Tableau) — the real correctness anchor:")
    print(f"    {engine_ok}/{engine_total} match"
          + (f"  ({100*engine_ok/engine_total:.1f}%)" if engine_total else
             "  (0 hand-checked — load Model.json into Power BI and fill powerbi_value)"))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
