#!/usr/bin/env bash
# One-command demo: compile the bundled Superstore workbook and evaluate it.
# Run from the repo root:  bash demo/run.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Compiling examples/Superstore.twbx"
python run_pipeline.py --twbx examples/Superstore.twbx

echo
echo "==> Proxy evaluation against Tableau ground truth"
python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv

echo
echo "==> Generated model for Tabular Editor / Power BI:"
echo "    data/Model.json"
echo "    data/powerbi_tom_model.json"
