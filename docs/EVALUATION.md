# Evaluation

This document explains how to measure whether the DAX that `tab2pbi` generates
actually reproduces Tableau's numbers, and — critically — what our automated
number does and does **not** prove.

> **Current status (Superstore):** engine-verified correctness is **1/1**
> (Power BI `0.1247` vs Tableau `0.1246721724`, hand-checked); proxy-correctness
> is **1/1**. Because the Power BI value was hand-read to 4 decimals, the
> engine-verified assertion uses a hand-read tolerance of `1e-3`:
> `python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv --tolerance 1e-3`.
> At the machine default `1e-6` the run shows 0/1 from display rounding alone,
> not a real mismatch — read full precision off Power BI if you need `1e-6`.

## The two numbers (do not conflate them)

The harness (`eval/evaluate.py`) reports two independent correctness figures:

| Number | What it compares | What it proves |
| ------ | ---------------- | -------------- |
| **proxy-correctness** | this repo's pandas AST-evaluator vs Tableau values | that the **parser / IR** captured the calculation |
| **engine-verified** | Power BI values (hand-recorded) vs Tableau values | that the **generated DAX** is correct in the real engine |

### ⚠️ Threat to validity — read this

The pandas evaluator (`src/tab2pbi/evaluation.py`) walks the **same AST** that
the DAX generator (`src/tab2pbi/rewrite/dax.py`) walks. If both share a
misconception — e.g. the AST mis-associates a field with the wrong table, or
mis-parses an operator — the pandas value and the generated DAX would be wrong
in the *same way*, and the proxy comparison against Tableau would still fail (or
pass) for reasons unrelated to the DAX string itself. In short:

> **proxy-correctness is a proxy for DAX semantics, not DAX itself.** It
> validates that our parser understood the Tableau formula; it does not execute
> a single line of the generated DAX.

The only way to prove the generated DAX is correct is to run it in the target
engine. That is the **engine-verified** number, and it is produced only from
values you hand-record after loading the generated model into Power BI /
Tabular Editor. When zero measures are hand-checked, the harness prints
`0/0` — it never lets the proxy number masquerade as engine-verified.

## Step 1 — Export ground truth from Tableau Desktop

For each measure you want to check, get the value Tableau itself computes:

1. Open the workbook in **Tableau Desktop**.
2. Create a new worksheet. Drag the calculated field (measure) onto **Text** (or
   Rows) with **no dimensions**, so you get the single grand-total value. (For a
   per-dimension check, add the dimension to Rows — the harness currently
   compares grand totals only; per-dimension support is a TODO.)
3. Read the value, or **Worksheet → Copy → Data** / **Worksheet → Export →
   Crosstab to CSV**.
4. Record it in the ground-truth CSV (see below). Use full precision.

## Step 2 — Fill the ground-truth CSV

`examples/eval/ground_truth_superstore.csv` has columns:

```csv
measure,tableau_value,powerbi_value
[Calculation_1368249927221915648],0.1246724548,
```

- `measure` — the calculation name exactly as in the model (with brackets).
- `tableau_value` — the value from Step 1 (source of truth).
- `powerbi_value` — **optional**; fill this only after Step 4.

> **Note on the bundled value:** the committed `tableau_value` for the
> Profit/Sales ratio was computed directly from the Hyper extract
> (`SUM(Profit)/SUM(Sales)` grand total) as a reproducible stand-in. Replace it
> with a value you actually read off Tableau Desktop to make the proxy number
> meaningful rather than circular.

## Step 3 — Run the proxy comparison

```bash
python run_pipeline.py --twbx examples/Superstore.twbx
python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv
```

This prints per-measure matches and the **proxy-correctness** percentage.

## Step 4 — Engine-verify (the real anchor)

1. Open `data/Model.json` in **Tabular Editor** (File → Open → From File) and
   save it into a Power BI dataset, or import into Power BI Desktop.
2. Put each generated measure on a card visual with no filters.
3. Read Power BI's value and write it into the `powerbi_value` column.
4. Re-run the harness. Now the **engine-verified** number is populated.

Even hand-checking a handful of measures gives a real correctness anchor that
the proxy number cannot provide. Record how many you checked in the handoff.

### Calculated columns are a row-level spot-check

The harness evaluates **grand-total scalars** (measures), so it cannot proxy a
row-level calculated column such as the generated
`DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)`. To engine-verify it,
pick one specific order in both tools and compare the per-row value directly
(Tableau row vs Power BI calculated-column value). This is a manual spot-check;
note the result in the handoff rather than in the CSV.
