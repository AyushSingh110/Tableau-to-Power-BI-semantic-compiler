# Example corpus

Workbooks used to exercise and evaluate the compiler. Kept small and
reproducible so anyone who clones the repo can run the full pipeline.

## Superstore.twbx

- **What:** Tableau's well-known "Sample - Superstore" dataset, packaged with an
  embedded Hyper extract (Orders / Returns / People tables).
- **Source:** Sample workbook distributed with Tableau Desktop / Tableau Public.
- **Why it's here:** it contains an embedded `.hyper` extract, which the
  pipeline needs end to end (schema + data-driven relationship inference). Many
  Tableau Public workbooks ship *without* extracts and cannot exercise the full
  pipeline.
- **License / redistribution:** "Sample - Superstore" is a fictional demo
  dataset provided by Tableau for learning and demonstration. It is widely
  redistributed in public repositories and tutorials. **This is not a formal
  license grant** — if you fork this repo for anything beyond personal/research
  use, confirm current Tableau sample-content terms and, if in doubt, replace it
  with your own workbook (`--twbx path/to/your.twbx`).

## Adding more workbooks

To keep the corpus reproducible **and** license-clean:

1. Prefer workbooks whose license clearly permits redistribution **and** that
   embed a Hyper extract.
2. If redistribution is unclear, do **not** commit the `.twbx`. Add a small
   download script and document the source URL here instead.
3. Record for every workbook: source URL, license, and whether it embeds an
   extract.

## expected_output/

A committed reference copy of the artifacts produced by running the pipeline on
`Superstore.twbx`. Regenerate with:

```bash
python run_pipeline.py --twbx examples/Superstore.twbx
cp data/*.json examples/expected_output/
```

## eval/

`ground_truth_superstore.csv` — Tableau-computed measure values used by the
evaluation harness. See [`../docs/EVALUATION.md`](../docs/EVALUATION.md).
