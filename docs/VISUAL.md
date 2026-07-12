# V1 Visual Compiler (Tableau worksheets → Power BI PBIR report)

Additive, isolated package `src/tab2pbi/visual/`. Emits a **Report only** (PBIR
`visual.json` + scaffolding); it does **not** emit a semantic model. Same
no-silent-drop discipline as the data-model compiler: every worksheet is either
emitted or **skipped with a taxonomy reason**.

## Run

```bash
# needs data/hyper_raw_data.csv (its header supplies the model's column names)
python run_pipeline.py --twbx examples/Superstore.twbx        # produces the CSV
python -m tab2pbi.visual --report-json data/visual_report/visual_conversion_report.json
# or, as a subcommand:  tab2pbi visual --report-json ...
```

Options: `--twbx`, `--entity` (default `hyper_raw_data`), `--columns-from`
(default `data/hyper_raw_data.csv`), `--out` (default
`data/visual_report/Superstore.Report`), `--model-path` (byPath to the paired
SemanticModel).

## ⚠️ Two honesty caveats (do not misread the output)

1. **Coverage is "emitted & schema-valid / total worksheets", NOT
   render-verified.** A schema-valid report is necessary but not sufficient —
   only Power BI Desktop confirms the visuals actually render. The summary prints
   `Render-verified: pending` until you do the gate below. (Same stance as
   proxy-vs-engine-verified on the model side.)
2. **Entity/model coherence gap (known, V2).** These visuals bind to a **flat**
   `hyper_raw_data` table — the spike's saved model. The data-model compiler
   emits a **multi-table TOM** (`Orders_ECFCA…`, `People`, …). **The two halves
   currently target different models**, so V1 visuals do **not** bind to the
   model compiler's output as-is. Unifying visual bindings with the multi-table
   TOM and adding a TMDL model emitter is **V2**. V1 is Report-only by design.

## Render-gate (the anchor — do this before calling V1 "done")

The emitted `Superstore.Report` references a sibling `../Superstore.SemanticModel`
(entity `hyper_raw_data`). A known-good paired model already exists in the repo
at `experiments/visual-spike/pbir_reference/Superstore.SemanticModel`.

1. Enable PBIP + PBIR preview features in Power BI Desktop (File → Options →
   Preview features; see `experiments/visual-spike/pbir_sample/README.md`).
2. Back up the reference report, then swap in the emitted one:
   ```bash
   cd experiments/visual-spike/pbir_reference
   mv Superstore.Report Superstore.Report.bak
   cp -r ../../../data/visual_report/Superstore.Report ./Superstore.Report
   ```
   (The emitted `definition.pbir` uses `byPath ../Superstore.SemanticModel`, which
   matches this layout, so it binds to the existing model with table
   `hyper_raw_data`.)
3. Open `experiments/visual-spike/pbir_reference/Superstore.pbip` in Power BI
   Desktop.
4. Confirm each emitted visual renders (column charts, the two bubble maps, the
   line/area/pie). If Desktop reports a **blocking error**, it names the
   offending file — inspect it in VS Code (the `$schema` line gives IntelliSense).
5. Record the result (renders / fixes needed) in `HANDOFF_REPORT.md`.

To restore the reference: `rm -rf Superstore.Report && mv Superstore.Report.bak
Superstore.Report`.

## Scope (V1)

- **Emit:** bar→`columnChart`, line→`lineChart`, area→`areaChart`,
  pie→`pieChart`, circle(2 measures)→`scatterChart`, text→`card`/`tableEx`,
  standard-geo dim + measure → `map` (bubble **approximation**).
- **Skip w/ reason:** `custom_shape`, `custom_geometry`, `map_choropleth`,
  `gantt`, `dual_axis`, `density`, `unsupported_mark`, `unmapped_encoding`,
  `insufficient_fields`, `unsupported_aggregation`.
- **Layout:** deterministic **auto-grid** (faithful Tableau dashboard positions =
  V2).
- **Aggregations:** `Sum` (`Function: 0`) is reference-verified; other
  aggregations use documented enum codes and, if not in the supported set, route
  to `unsupported_aggregation` rather than emitting a guessed code.

## Validation

1. **Structural** conformance to the ground-truth `pbir_reference` skeleton —
   enforced; a deviation aborts emission.
2. **JSON-schema** against the pinned `visualContainer/2.3.0` — best-effort;
   currently reports `skipped (schema not vendored)` because the schema's remote
   `$ref` tree cannot be resolved offline. The structural gate is the substantive
   check (it diffs against real Power BI output).

---

# V2 — end-to-end `.pbip` (model + visuals, coherently bound)

V2 unifies the two halves: `.twbx` → a full **`.pbip`** = a **TMDL SemanticModel**
(the compiler's own multi-table model) + a **PBIR Report** whose visuals bind to
that model's real tables — not the flat spike table.

```bash
python -m tab2pbi build-pbip                      # or: tab2pbi build-pbip
#   → data/pbip/Superstore.pbip
#     data/pbip/Superstore.SemanticModel/  (TMDL: model, tables, relationships)
#     data/pbip/Superstore.Report/         (PBIR visuals byPath → the model)
```

Options: `--twbx`, `--out` (default `data/pbip`), `--name`, `--data-dir`.

## Data source (how the model actually loads data)

Each TMDL table gets a **CSV import partition** sourcing the per-table CSV the
pipeline already generates (`data/tables/*.csv`), with M code modeled on the
reference SemanticModel.

> ⚠️ **The `File.Contents(...)` path is ABSOLUTE** (as Power BI itself emits) so
> the `.pbip` opens on this machine without hand-editing. **Moving the repo
> breaks the path and the model loads empty — re-run `build-pbip` to
> regenerate the CSVs and re-emit the absolute paths.** `--csv-dir` overrides the
> base path.

## ⚠️ Known deltas (documented, not bugs)

- **No auto date-tables** (`__PBI_TimeIntelligenceEnabled = 0`): "by Order Date"
  charts render against a **flat date column**, not a date hierarchy. This is an
  expected simplification, *not* a binding failure.
- **Multi-line DAX is skipped** in TMDL (a measure/column/parameter whose DAX
  spans lines is not emitted — it would break model load). Counted in the build
  report as `tmdl_skipped_multiline`. On Superstore: 1 parameter (viz-instruction
  text).
- **Layout is faithful-but-not-pixel-perfect**: dashboard zones → page positions,
  clamped to a visible minimum and kept on-canvas; tiny/hidden helper-sheet zones
  become small on-canvas tiles rather than 1px slivers.
- **Measure / calc-column TMDL is the #1 render risk** — it's the one part not
  grounded in the reference (which has no measures). We emit only minimal valid
  properties. *If the model fails to load and the error points at a measure or
  column, that's the place to look* — create one measure + one calc column
  manually in Tabular Editor/Power BI, save to `.pbip`, and use it as TMDL ground
  truth (same approach we used for `visual.json`).

## Render-gate (the anchor — pending until you run it)

1. Enable **PBIP + PBIR + TMDL** preview features in Power BI Desktop
   (File → Options → Preview features).
2. Open `data/pbip/Superstore.pbip`.
3. Confirm **(a) the model loads**: tables `Orders_ECFCA…`, `People_…`,
   `Returns_…`; the relationship `Orders.Region → People.Region`; the measure
   `Calculation_1368…` and the `DATEDIFF` calc column.
4. Confirm **(b) the visuals render** and bind to the compiler's tables (the
   column charts, the two bubble maps, area/pie/line).
5. Note **(c) any visual that broke vs the V1 flat-model render** — especially
   anything expecting a date hierarchy (see deltas above).
6. Record the result in `HANDOFF_REPORT.md`. **Structure-valid ≠ renders** — only
   Power BI confirms it.
