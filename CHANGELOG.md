# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and the project uses
semantic-ish versioning.

## [Unreleased]

## [0.2.0] — Phase 2: research-grade

### Added
- **Real tokenizer + Pratt parser** (`ir/tokenizer.py`, `ir/parser.py`) replacing
  the regex AST builder. Produces a typed AST (`constant`, `field`,
  `aggregation`, `binary`, `comparison`, `logical`, `not`, `unary`,
  `conditional`, `function`, `unsupported`, `parse_error`). Never crashes —
  unparseable input becomes a `parse_error` node with a reason.
- **Broadened AST→DAX transpiler** (`rewrite/dax.py`): aggregations, algebraic
  combinations, `COUNTD→DISTINCTCOUNT`, `IF`/`CASE`→`IF`/`SWITCH`, `DATEDIFF`,
  `YEAR`/`MONTH`/`DAY`, `ABS`/`ROUND`/`INT`/`ZN`. Unsupported families raise a
  taxonomy-tagged error and are skipped with a reason.
- **Measure vs. calculated-column split** by aggregation presence; constant
  calcs classified as **parameters** (own bucket, with a note that a Power BI
  What-If/field parameter is the faithful target — kept out of the coverage
  headline).
- **Machine-readable failure taxonomy** in the conversion report
  (`lod_expression`, `table_calc`, `window_fn`, `custom_sql`, `parse_error`,
  `unsupported_fn`, …) with counts and coverage %.
- **Versioned IR JSON Schemas** (`ir/schema/*.v1.schema.json`) + `ir/validate.py`;
  the pipeline validates the semantic model and final model each run.
- **Evaluation harness** (`eval/evaluate.py`, `evaluation.py`) reporting
  **proxy-correctness** (pandas AST vs Tableau) and **engine-verified** (Power BI
  vs Tableau) as separate numbers; `docs/EVALUATION.md` documents the export
  steps and names the shared-AST threat to validity.
- **pytest suite** (parser, transpiler, evaluator, schema, golden E2E) and a
  **GitHub Actions** CI workflow (pytest + ruff on 3.10/3.12).
- **`docs/ARCHITECTURE.md`** (IR spec, semantic-mismatch, related work) and two
  **Mermaid diagrams** + IR rationale in the README.
- `examples/README.md` documenting corpus provenance/licensing.

### Changed
- Classification and the conversion report are now driven by transpiler
  outcomes; converted DAX is split across measures/columns/parameters.
- Fixed a tokenizer bug where `//` inside a string literal (e.g. `https://…`)
  was stripped as a comment.

### Known gaps
- Declared TWB relationships are extracted but **not merged** into the model.
- Conditional/parameter-dependent aggregations not yet transpiled.
- Evaluation compares grand totals only.

## [0.1.0] — Phase 1: honest & reproducible + Phase 3: demo

First version where the pipeline runs **end to end** on the sample workbook.

### Added
- `build_semantic_model` step (`ir/semantic_model.py`) — the previously missing
  stage that produces the AST-shaped `semantic_model.json` the context stage
  needs. Un-buildable calculations become `unsupported` nodes with a reason.
- Deterministic AST builder (`ir/ast_builder.py`) recognizing single and
  algebraic-binary aggregations; everything else is unsupported-with-reason.
- `run_pipeline.py` single-command orchestrator and a `tab2pbi` CLI
  (`tab2pbi run <workbook.twbx>`) with a clean summary report.
- `--fact-table` override; fact/dimension is now a documented, overridable
  heuristic (largest table by column count) recorded in provenance and the
  conversion report, with affected measures flagged.
- Packaged source under `src/tab2pbi/{parse,classify,rewrite,relationships,ir,export}/`.
- `LICENSE` (MIT), `CONTRIBUTING.md`, `CHANGELOG.md`, `pyproject.toml`.
- Labeled sample outputs under `examples/expected_output/`.

### Changed
- Relationship inference (`relationships/from_hyper.py`) now profiles each
  physical table's own data. Previously it read one un-prefixed CSV, so its
  table split was always empty and it silently emitted zero relationships. It
  now infers the real `Orders.Region → People.Region` relationship.
- Classification (`classify/`) and DAX rewriting (`rewrite/`) are driven by the
  parsed AST instead of substring matching, so large formatting / table-calc
  formulas are no longer mislabeled "simple aggregation" and copied verbatim as
  invalid DAX.
- Converted DAX is now table-qualified (e.g. `SUM(Orders[Profit])`).
- All paths are CLI arguments; no more hardcoded `Superstore.twbx`.
- `requirements.txt` versions pinned.
- README rewritten to describe only what actually runs.

### Removed
- Ten standalone top-level scripts, replaced by the `tab2pbi` package.
- Orphan `data/parsed_visuals.json` (no producer, no consumer).
- Generated `data/*` artifacts are no longer tracked (regenerate via the CLI).

### Moved
- `Superstore.twbx` → `examples/Superstore.twbx`.
