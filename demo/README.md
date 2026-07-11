# Demo — Superstore, end to end

A five-minute walkthrough: a Tableau workbook in, a Power BI model out, opened
in Tabular Editor.

## 1. One command

From the repo root:

```bash
# macOS/Linux
bash demo/run.sh
# Windows PowerShell
./demo/run.ps1
```

This compiles `examples/Superstore.twbx` and runs the evaluation harness.

## 2. What you should see

```
============================================================
 tab2pbi summary — Superstore.twbx
============================================================
 Tables:              3
 Calculations total:  17
   measures:          1
   calc columns:      1
   parameters:        4
   skipped:           11
 Coverage:            11.8%
 Relationships:       1
 Fact table:          Orders_… (inferred_by_size)
 Failure taxonomy:
   unsupported_fn           4
   table_calc               2
   window_fn                2
   unresolved               1
   aggregate_of_expression  1
   empty_formula            1
============================================================
```

And from the evaluation harness:

```
 PROXY-correctness (pandas AST vs Tableau) — validates parser, NOT DAX:
   1/1 match  (100.0%)
 ENGINE-verified (Power BI vs Tableau) — the real correctness anchor:
   0/0 match  (0 hand-checked — load Model.json into Power BI and fill powerbi_value)
```

> The proxy number is **not** engine-verified correctness. See
> [`../docs/EVALUATION.md`](../docs/EVALUATION.md).

## 3. Inspect the generated model

The pipeline writes a Tabular Editor–compatible model to `data/Model.json` and a
Power BI TOM to `data/powerbi_tom_model.json`. The converted measure is
table-qualified DAX:

```
[Calculation_1368…] = SUM(Orders_…[Profit]) / SUM(Orders_…[Sales])
```

the row-level `DATEDIFF` became a calculated column, the four constant
calculations are surfaced as parameters (annotated), and the 11 unconvertible
calculations are recorded with reasons — nothing is dropped silently.

## 4. Open it in Tabular Editor

1. Install [Tabular Editor 2 (free)](https://tabulareditor.com/) or 3.
2. **File → Open → From File…** and choose `data/Model.json`.
3. Expand the **Orders** table to see the generated measure, the `DATEDIFF`
   calculated column, and the parameter columns; expand **Model → Relationships**
   to see `Orders → People`.

### Screenshots

> **Placeholder — screenshots to be added by the author.** I (the assistant)
> cannot launch Tabular Editor in this environment, so the images below are
> intentionally left as placeholders. Capture them once and drop the PNGs into
> [`screenshots/`](screenshots/); the filenames are already referenced here.

| Step | Image |
| ---- | ----- |
| Model tree (tables, measure, calc column, parameters) | `screenshots/01-model-tree.png` |
| The generated measure's DAX in the expression editor | `screenshots/02-measure-dax.png` |
| The `Orders → People` relationship | `screenshots/03-relationship.png` |

<!-- Once captured, embed them, e.g.:
![Model tree](screenshots/01-model-tree.png)
-->

See [`screenshots/README.md`](screenshots/README.md) for exactly what each image
should show.
