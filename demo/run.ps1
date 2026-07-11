# One-command demo (Windows PowerShell): compile + evaluate the Superstore workbook.
# Run from the repo root:  ./demo/run.ps1
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "==> Compiling examples/Superstore.twbx"
python run_pipeline.py --twbx examples/Superstore.twbx

Write-Host "`n==> Proxy evaluation against Tableau ground truth"
python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv

Write-Host "`n==> Generated model for Tabular Editor / Power BI:"
Write-Host "    data/Model.json"
Write-Host "    data/powerbi_tom_model.json"
