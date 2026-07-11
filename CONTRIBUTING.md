# Contributing

Thanks for your interest in `tab2pbi`. This is a research-oriented project with
a strict design philosophy — please read it before opening a PR.

## Design principles (non-negotiable)

1. **Deterministic.** Same input → same output. No randomness, no time- or
   environment-dependent behavior.
2. **No silent drops, no fabrication.** If a calculation cannot be translated,
   emit it as `unsupported` **with a reason**. Never invent a mapping or a DAX
   expression you cannot justify from the source.
3. **Heuristics are labeled as heuristics.** Anything inferred (e.g. the fact
   table by size) must be recorded in the model's provenance / conversion
   report, and must be overridable.
4. **Official interfaces only.** Tableau Hyper API for extracts; documented TWB
   XML structures for metadata.

## Development setup

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running

```bash
python run_pipeline.py --twbx examples/Superstore.twbx
# or, once installed:
tab2pbi run examples/Superstore.twbx
```

## Before submitting

- `ruff check .` passes.
- `pytest` passes (unit stages + the golden end-to-end test).
- One logical change per commit; use Conventional Commit messages
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).
- If behavior changes, update `CHANGELOG.md`.

## Project layout

```
src/tab2pbi/
  parse/          # .twbx -> parsed metadata + hyper schema/data + mapping
  ir/             # AST semantic model, table-context, canonical, finalize
  classify/       # AST-driven convertibility classification (report-only)
  rewrite/        # AST -> table-qualified DAX
  relationships/  # declared (TWB) + data-driven (Hyper) relationships
  export/         # Power BI TOM + Tabular Editor Model.json
  pipeline.py     # stage orchestration
  cli.py          # `tab2pbi` command
```
