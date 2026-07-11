# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/) and the project uses
semantic-ish versioning.

## [Unreleased]

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
