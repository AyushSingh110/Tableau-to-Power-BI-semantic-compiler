# Handoff Report — tab2pbi (Tableau → Power BI semantic compiler)

**Scope of this report:** Phase 2 (research-grade) Part A (architecture docs),
Part B (parser + transpiler + schema + tests + CI + eval), and Part C (demo).
Written to be self-contained — you can paste it into another assistant without
repo access to plan the next step.

`tab2pbi` compiles a Tableau `.twbx` into a Power BI Tabular Object Model (TOM)
via a canonical semantic IR. It is deterministic and never fabricates: every
un-translated calculation is reported with a reason and a failure-taxonomy
bucket.

---

## ⚠️ Open items needing me (the human)

These are the only things blocking a fully-anchored result. None block the code.

1. ~~**Engine-verify correctness in Power BI (the real anchor).**~~ **DONE.**
   - The generated measure `[Calculation_1368249927221915648]`
     (`SUM(Orders[Profit]) / SUM(Orders[Sales])`) was hand-checked in Power BI
     Desktop against the same Superstore data: Power BI reads **0.1247**, Tableau
     reads **0.1246721724** — a match to the 4 decimals hand-read off the card.
     `powerbi_value=0.1247` is recorded in
     `examples/eval/ground_truth_superstore.csv`.
   - **Tolerance note (honest, reproducible):** because the value was hand-read
     to 4 decimals, engine-verification is asserted at a hand-read tolerance of
     `1e-3`, not the machine default `1e-6`. Reproduce with:
     `python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv --tolerance 1e-3`
     → **engine-verified 1/1 (100%)**. At the default `1e-6` the same run shows
     0/1 purely from display rounding, not a real error.
   - **Calculated column** `DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)`:
     row-level spot-check pending in Power BI (add the column, compare one order's
     delay to Tableau). Low risk; not blocking.
   - Current status: **engine-verified 1/1 (proxy 1/1).**

2. **Confirm the `from_twb` dead-end decision (raised in Part A).**
   Declared TWB relationships are extracted to `relationships_from_twb.json` but
   **not merged** into the canonical/final model — only data-driven ones reach
   the TOM. For Superstore the declared relationships are key-less query-time
   joins (nothing actionable), but a workbook with explicit physical-join keys
   would have them recorded-but-not-applied. **Decision needed:** implement a
   merge of actionable declared relationships (Part-B TODO), or accept
   data-driven-only and keep the documented note. See README stage guarantee +
   `docs/ARCHITECTURE.md §4`.

3. **Superstore redistribution / license.**
   `examples/Superstore.twbx` is Tableau's sample dataset, widely redistributed
   but **without a formal license grant** in this repo. Confirm current Tableau
   sample-content terms before publishing the repo publicly, or swap in your own
   workbook. Provenance is documented in `examples/README.md`.

---

## What was done, per part

### Part A — architecture documentation (README)
| Change | Rationale |
| ------ | --------- |
| Added `## Architecture` with a **Mermaid flowchart** matching real `src/tab2pbi` modules | Replace the old "11-stage" fiction with the true data flow |
| Per-stage **input → output → guarantee** bullets | Make each stage's contract explicit |
| **"Why an IR"** + semantic-mismatch table (LOD/table-calc, row-vs-agg, deferred joins, field identity) | Explain the core abstraction and the problem it solves |
| Second **Mermaid class diagram** of the IR data model | One-glance view of Tables/Columns/Measures(AST)/Relationships |
| Documented `from_twb` dangling node as a **known gap** (diagram note + stage guarantee + Known limitations) | Honesty: extracted-but-unmerged relationships must not look silently dropped |

### Part B — research rigor
| File | Change | Rationale |
| ---- | ------ | --------- |
| `src/tab2pbi/ir/tokenizer.py` | **New.** Tokenizer for Tableau calc syntax | Real lexing, comments handled in-loop (so `//` inside strings survives) |
| `src/tab2pbi/ir/parser.py` | **New.** Pratt parser → typed AST; `build_ast` never raises | Structured parsing; garbage → `parse_error` node, never a crash |
| `src/tab2pbi/ir/ast_utils.py` | **New.** Tree walk / `has_aggregation` / `field_tables` | Shared AST traversal for context, transpiler, evaluator |
| `src/tab2pbi/ir/ast_builder.py` | **Removed.** | Replaced by tokenizer+parser |
| `src/tab2pbi/rewrite/dax.py` | **Rewritten.** AST→DAX visitor + `TranspileError(taxonomy)`; measure/column/parameter split | Broader coverage; precise skip reasons; correct DAX placement |
| `src/tab2pbi/ir/context.py` | **Rewritten.** Recursively annotate `field` nodes with owning table | Table-qualified DAX; supports the richer AST |
| `src/tab2pbi/classify/classifier.py` | **Rewritten.** Report aligned to transpiler outcomes | Single source of truth; report-only |
| `src/tab2pbi/ir/canonical.py`, `finalize.py` | Measures attached in finalize; report gains `coverage_pct`, `failure_taxonomy`, buckets | Machine-readable audit |
| `src/tab2pbi/ir/schema/*.v1.schema.json`, `ir/validate.py` | **New.** Versioned IR JSON Schemas + validation wired into pipeline | Formalize the IR; fail loudly on malformed output |
| `src/tab2pbi/evaluation.py` | **New.** pandas AST evaluator (grand-total scalars) | Proxy correctness against Tableau |
| `eval/evaluate.py` | **New.** Harness reporting proxy + engine-verified separately | Correctness with an explicit validity caveat |
| `src/tab2pbi/export/tom.py`, `cli.py`, `pipeline.py` | Emit calc columns + parameters; new summary/report keys; reordered stages | Support the split + validation |
| `tests/` | **New.** `test_parser`, `test_transpiler`, `test_evaluation`, `test_schema`, `test_golden_e2e` | Unit per module + golden E2E (written first, kept green through the rewrite) |
| `.github/workflows/ci.yml` | **New.** pytest + ruff on push (3.10/3.12) | CI |
| `docs/ARCHITECTURE.md` | **New.** IR spec, semantic mismatch, related work (Calcite/sqlglot; Lenzerini; Cheney/Buneman provenance) | Frame as a tools/systems contribution |
| `docs/EVALUATION.md` | **New.** Export steps + the shared-AST **threat to validity** | Don't let proxy masquerade as engine-verified |
| `examples/README.md`, `examples/eval/ground_truth_superstore.csv` | **New.** Corpus provenance + ground-truth stand-in | Reproducible corpus |

### Part C — demo
| File | Change |
| ---- | ------ |
| `demo/run.sh`, `demo/run.ps1` | One-command compile + evaluate |
| `demo/README.md` | Walkthrough (input → run → model → Tabular Editor) with **labeled screenshot placeholders** |
| `demo/screenshots/README.md` | Exactly what each screenshot should show (author to capture) |

---

## Before/after metrics (Superstore)

| Metric | Start of Phase 2 | Now |
| ------ | ---------------- | --- |
| Measures converted | 1 | 1 (anchor unchanged) |
| Calculated columns | 0 | 1 (`DATEDIFF`) |
| Parameters (own bucket) | 0 | 4 (constants) |
| Skipped | 16 (coarse) | 11 (taxonomy-tagged) |
| Coverage (measures+cols/total) | ~6% | **11.8%** |
| Relationships | 1 | 1 |
| Proxy correctness | n/a | **1/1 (100%)** |
| Engine-verified correctness | n/a | **0/0 (pending hand-check)** |
| Tests | 6 (golden only) | **39** |
| CI | none | pytest + ruff |

**Failure taxonomy now:** `unsupported_fn` 4 (mostly `STR`), `table_calc` 2
(`RANK_UNIQUE`, `INDEX`), `window_fn` 2 (`WINDOW_MAX/MIN`),
`aggregate_of_expression` 1 (`SUM(ZN(IF …))`), `unresolved` 1 (references another
calc field), `empty_formula` 1 (a Tableau group).

**Why coverage is still modest (not a regression):** the Superstore workbook is
dominated by table calcs, window functions, and `STR`/`LOG`/`POWER` string
formatting that are genuinely out of scope. The gains are real; the number was
deliberately *not* inflated (constants are excluded from the headline).

---

## Decisions I made that were not explicitly specified

1. **Coverage excludes parameters** (measures+columns / total). Per your
   refinement, constants are surfaced as parameters in their own bucket so four
   constants don't inflate the headline.
2. **AST node vocabulary** (`constant/field/aggregation/binary/comparison/
   logical/not/unary/conditional/function/unsupported/parse_error`). Chosen to
   cover the triage list while staying small.
3. **DAX mappings:** `AVG→AVERAGE`, `COUNTD→DISTINCTCOUNT`, multi-branch
   `IF/CASE→SWITCH(TRUE(), …)`, single-branch `→IF()`, `AND/OR→&&/||`,
   `DATEDIFF('day',a,b)→DATEDIFF(a,b,DAY)`, `ZN→COALESCE(x,0)`. These are the
   conventional equivalents; the ones I was unsure about (see below) are skipped.
4. **String concat `+` left as `+`** (not `&`). Without type inference I cannot
   safely tell numeric `+` from string concat; the affected formatting measures
   are skipped for other reasons anyway. **Open question** if you want string
   concat support.
5. **Aggregation only over a plain field**; `SUM(<expression>)` (e.g.
   `SUM(ZN(IF …))`) is skipped as `aggregate_of_expression` rather than guessed
   as `SUMX`. Honest but conservative.
6. **Fact table = largest by column count**, overridable via `--fact-table`
   (carried over from Phase 1); flagged in the report when inferred.
7. **Evaluator scope = grand-total scalars.** Row-level columns / conditionals
   are `not_evaluated` by the proxy. Per-dimension is a TODO.
8. **Ground-truth stand-in** value computed from the extract
   (`SUM(Profit)/SUM(Sales)`), clearly labeled to be replaced by a real Tableau
   export. It is a placeholder, not a claim.
9. **JSON Schemas cover semantic_model + final_model** (the two that matter most)
   rather than every intermediate artifact.

---

## Known issues / TODOs / open questions

- **[open, needs you]** Merge actionable declared TWB relationships (item 2 above).
- **TODO** Conditional aggregations / parameter-dependent measures
  (`SUM(IF year=[Parameter] …)`) → `CALCULATE`/`SUMX` with inlined parameters.
- **TODO** Per-dimension correctness in the eval harness (currently grand totals).
- **TODO** String-concat `+` → `&` with light type inference.
- **TODO** `STR`/`FORMAT`, `DATEPARSE`, `LOG`/`POWER` for the SI-formatting measures.
- **Limitation** TOM calculated columns are emitted without an explicit
  `dataType` (engine infers on load); confirm this is acceptable in your target.
- **Open question** Should parameters become Power BI **What-If/field
  parameters** rather than constant calculated columns? (Currently a column +
  note.)

---

## Commands verified working (this session)

All run from the repo root; Python 3.13 locally (CI covers 3.10/3.12).

```bash
# Full pipeline (deterministic; regenerates data/)
python run_pipeline.py --twbx examples/Superstore.twbx
#   → Tables 3 | measures 1, calc columns 1, parameters 4, skipped 11
#   → Coverage 11.8% | Relationships 1 | Fact Orders (inferred_by_size)

# Evaluation harness
python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv
#   → PROXY-correctness 1/1 (100.0%)
#   → ENGINE-verified 0/0 (0 hand-checked)

# Tests + lint (both green)
python -m pytest -q            # 39 passed
python -m ruff check src tests run_pipeline.py eval   # All checks passed!

# One-command demo
bash demo/run.sh               # compile + evaluate, prints model paths
```

Determinism spot-check: regenerated `data/*.json` byte-match
`examples/expected_output/` for the golden run.

---

## Not committed / tagging

Per your instruction, **nothing was committed**. The working tree contains all
Part A/B/C changes (≈10 modified source files, new `tests/`, `docs/`, `eval/`,
`demo/`, `.github/`, `src/tab2pbi/ir/{tokenizer,parser,ast_utils,validate}.py`,
`src/tab2pbi/evaluation.py`, `ir/schema/`; `ir/ast_builder.py` deleted).

After you commit, create the milestone tag:

```bash
git tag -a v0.2-research -m "Phase 2: research-grade + demo"
```

Suggested logical commits (one change each): `feat: tokenizer+parser`,
`feat: broaden DAX transpiler + measure/column/parameter split`,
`feat: IR JSON-Schema validation`, `feat: evaluation harness + docs`,
`test: unit + golden e2e`, `ci: pytest+ruff workflow`,
`docs: architecture + README diagrams + demo`.

---

## Paper draft (tool-demo / workshop paper)

**Location:** `docs/paper/paper.md` (Markdown, ~4–6 pages equivalent) +
`docs/paper/references.bib`. Convert to the workshop LaTeX template later.

**What's written:** Abstract + 10 sections — Introduction/motivation, the
semantic-mismatch problem (README mismatch table), method/architecture
(pipeline + IR + AST measure-vs-column split + relationship inference), the
failure taxonomy (counts table), evaluation methodology (two numbers +
threat-to-validity + tolerance rationale), results, demo (Fig. 1 placeholder),
related work (positioned, not claiming kinship), limitations/future work,
reproducibility appendix.

**Framing (as approved):** honesty/rigor is the contribution, not coverage; the
11.8% is presented as a *finding*. Data-integration and provenance references
are used as **vocabulary only** (1–2 sentences each), explicitly not claiming a
theoretical contribution. Engine-verified is presented as an honest **n=1**
hand-anchor.

**Every number is pinned** to its source with an inline `<!-- source: -->`
comment (abstract included — grep `source:` to audit). Pins:

| Number in paper | Pinned to |
| --------------- | --------- |
| 3 tables, 17 calcs, 1 measure, 1 column, 4 params, 11 skipped, 11.8% | `data/final_powerbi_semantic_model.json` → `conversion_report`, via `python run_pipeline.py --twbx examples/Superstore.twbx` |
| failure taxonomy (4/2/2/1/1/1) | `conversion_report.failure_taxonomy` |
| 1 relationship, coverage 1.0 | `data/inferred_powerbi_relationships.json` |
| proxy 1/1; engine-verified 1/1 @1e-3 (0/1 @1e-6) | `python eval/evaluate.py --ground-truth examples/eval/ground_truth_superstore.csv --tolerance 1e-3` |
| Tableau 0.1246721724 vs Power BI 0.1247 | `examples/eval/ground_truth_superstore.csv` |
| 39 tests | `python -m pytest -q` |

**`[CITATION NEEDED]` / verification items (must be resolved before submission):**

1. **`paper.md` §1** — `[CITATION NEEDED — verify specific claims about existing
   commercial Tableau→Power BI migration tools]`. The motivation asserts that
   existing tools do visual/best-guess conversion and silently drop calcs. I have
   **no verifiable source** for that specific claim; either cite a real
   comparison/survey or soften the sentence to a general observation.
2. **`references.bib` (all entries)** — author/title/venue/year are for
   well-established works and believed correct, but **exact DOIs, page numbers,
   and publisher fields are NOT included/verified**. Verify each against
   DBLP/ACM before camera-ready (noted at the top of the `.bib`).
3. **`sqlglot` entry** — cited as `@misc` software (Mao, GitHub URL, accessed
   2026-07-11), per decision; confirm the URL/author attribution.
4. **Figure 1** — `demo/screenshots/01-model-tree.png` is a placeholder; the
   screenshot must be captured before the paper has a real figure.

**Not committed.** `docs/paper/` is new, `HANDOFF_REPORT.md` modified. Suggested
commit: `docs: add tool-demo paper draft + references`.

## V1 visual compiler (Tableau worksheets → Power BI PBIR report)

**What was built** — additive, isolated package `src/tab2pbi/visual/` (existing
data-model pipeline untouched and still green: 6/6 golden, full suite 58 passed,
ruff clean). Modules: `ir.py` (Visual IR + failure taxonomy), `mapping.py`
(deterministic mark→visual table), `extract.py` (.twb → PageNodes, reuses
`ir.context.normalize_field_name`, resolves real-world column names), `emit_pbir.py`
(emits PBIR `visual.json` pinned to `visualContainer/2.3.0` + scaffolding + bundled
theme; structural validation against the ground-truth reference), `report.py`,
`cli.py` (+ `visual` subcommand and `python -m tab2pbi.visual`). Ground truth =
the human-provided `experiments/visual-spike/pbir_reference/` (real Power BI
output; entity `hyper_raw_data`, map uses `visualType:"map"`, `Function:0`=Sum).

**Real coverage (Superstore, 32 worksheets)** — from
`python -m tab2pbi.visual`:

| | count |
| - | - |
| Visuals emitted | **9** (columnChart 4, map 2, areaChart 1, pieChart 1, lineChart 1) |
| Skipped | **23** — `custom_shape` 11, `insufficient_fields` 8, `custom_geometry` 2, `gantt` 1, `dual_axis` 1 |
| Coverage | **28.1%** (emitted & schema-valid / total worksheets) |

**Render-gate result: ✅ VERIFIED — 9/9 rendered (2026-07-12).** The emitted
Report was paired with the reference `Superstore.SemanticModel` (entity
`hyper_raw_data`) and opened in Power BI Desktop. All 9 emitted visuals rendered
with real data: 4 column charts (Order Date, Category, Category+Order Date,
Sub-Category, Product Name), 2 bubble maps (State, City), 1 line (Segment), 1 pie
(Sub-Category), 1 area. Coverage **28.1%** is now **render-verified**, not just
schema-valid.

**Honest map finding (geocoder divergence, as predicted in V0):** the "Sales by
City" map scatters bubbles worldwide — Power BI's Bing geocoder resolves
ambiguous US city names to foreign cities. The visual renders correctly but
geographic fidelity is imperfect. This is concrete evidence for the paper's
"maps translate analytical *intent*, not exact geography" claim, and reinforces
the choropleth/custom-geometry skip decisions. Not a defect — a documented
boundary of the Tableau→Power BI geocoding mismatch.

**⚠️ Entity/model coherence gap (known, not solved).** The visual layer binds to
a **flat `hyper_raw_data`** table (the spike's saved model); the data-model
compiler emits a **multi-table TOM** (`Orders_ECFCA…`, `People`). **The two halves
target different models today — V1 visuals do NOT bind to the model compiler's
output as-is.** This is acceptable for V1 (Report-only) but is a real integration
gap: unifying visual bindings with the multi-table TOM + a **TMDL model emitter**
is **V2**. Not hand-waved as end-to-end.

**Decisions I made that weren't specified:**
- **Auto-grid layout** (deterministic 3-col grid); faithful Tableau dashboard
  positions deferred to V2 (as approved).
- **Primary-mark priority** (Multipolygon > GanttBar > Pie > Bar > Line > Area >
  Circle > Shape > Text > Automatic) to pick one visual per multi-mark worksheet;
  **dual-axis** flagged only when ≥2 distinct marks from {Bar,Line,Area} co-occur
  (so a map with pie overlays is not mis-skipped).
- **Aggregation codes:** only `Sum` (`Function:0`) is reference-verified; avg/min/
  max/count use documented enum codes, and any aggregation outside the supported
  set routes to `unsupported_aggregation` rather than a guessed code.
- **Deterministic ids** = `sha1(name)[:20]`.
- **Validation:** structural conformance to the reference is the *enforced* gate;
  JSON-schema against 2.3.0 is best-effort and currently reports `skipped (schema
  not vendored)` — the schema's remote `$ref` tree won't resolve offline. Honest,
  not hidden.
- **Text→card vs tableEx** split by presence of a dimension; **Circle needs 2
  measures** or it's `insufficient_fields` (no broken scatter).

**V1 tests (19 new, wired into CI):** `test_visual_mapping`, `test_visual_extract`
(incl. real-world `Sub-Category`/`Country/Region`/`Order Date` resolution + a
calc-field → unmapped case), `test_visual_emit` (emitted JSON structurally matches
the reference map skeleton), `test_visual_golden` (the 9-emitted / 23-skipped
snapshot).

**V1 next steps (ranked):** (1) **run the render-gate** and record it; (2) **TMDL
model emitter** + unify visual bindings with the multi-table TOM (closes the
coherence gap); (3) **faithful dashboard layout/position** (replace auto-grid);
(4) **broader mark coverage** (dual-axis combo charts, more geo/choropleth,
scatter refinements); (5) vendor the PBIR schema for the best-effort gate.

## V2 end-to-end pipeline (.twbx → full .pbip)

**What was built** — additive, existing pipeline + V1 untouched and green
(**74 tests pass**, ruff clean). V2 unifies the two halves into one command:

- `src/tab2pbi/export/tmdl.py` — **TMDL model emitter**: canonical model → a
  `*.SemanticModel/` folder (`model.tmdl`, `database.tmdl`, `relationships.tmdl`,
  `cultures/en-US.tmdl`, `tables/*.tmdl` with columns + import partition +
  measures + calc columns). Structure grounded in the reference SemanticModel;
  measure/calc-column syntax grounded in the official TMDL docs.
- `src/tab2pbi/visual/extract.py` — **coherent binding**: `multitable_resolver`
  binds each field to its real owning table (fact-preferred for ambiguous names);
  unresolved → `unmapped_encoding`. Flat `--entity` mode kept as fallback.
- `src/tab2pbi/visual/layout.py` — **dashboard layout**: zones → PBIR page
  positions (largest zone per sheet, clamped visible, on-canvas); auto-grid
  fallback for loose sheets.
- `src/tab2pbi/build_pbip.py` + `tab2pbi build-pbip` — orchestrates
  `.twbx` → `.SemanticModel/` + `.Report/` (byPath → the model) + `.pbip` pointer
  + `build_report.json`.

**Does the unified `.pbip` open with model + visuals?** Structurally yes — it
emits a complete `.pbip` and all 74 tests pass — but **render is PENDING**
(pending your Power BI check; see `docs/VISUAL.md` V2 render-gate).

**Coverage (Superstore, `tab2pbi build-pbip`):**

| | |
| - | - |
| Model | 3 tables, **1 measure**, 1 calc column, 3 parameters, 1 relationship; **1 multi-line param skipped** (would break TMDL) |
| Visuals | 32 worksheets → **9 emitted** (columnChart 4, map 2, area/pie/line 1), **23 skipped** by bucket; **all bound to `Orders_ECFCA…`**, not flat `hyper_raw_data` |

**Data-source strategy:** one **CSV import partition per table** from the
generated `data/tables/*.csv`, M grounded on the reference. The `File.Contents`
path is **absolute** so it opens here without hand-editing — **moving the repo
breaks it; re-run to regenerate** (documented in output + `docs/VISUAL.md`).

**Decisions I made (unspecified):**
- **Multi-line DAX → skipped** in TMDL (not emitted as fragile/invalid TMDL),
  counted as `tmdl_skipped_multiline`. Protects model load (refinement #1).
- **Auto date-tables skipped** (`__PBI_TimeIntelligenceEnabled = 0`) → "by Order
  Date" charts render flat dates, not a hierarchy (documented delta, not a bug —
  refinement #3).
- **Layout clamped** to a 120×90 minimum + on-canvas so hidden/tiny designer
  zones don't become 1px slivers (faithful-not-pixel-perfect).
- **Deterministic uuid5 lineageTags**; page/visual ids = `sha1(name)[:20]`.
- **No DAX rewrite needed** — model measures already reference multi-table
  entities (refinement #4 was a no-op, as predicted).

**Render-gate result: ✅ VERIFIED end-to-end (2026-07-12).** The unified
`data/pbip/Superstore.pbip` opened in Power BI Desktop; after **Refresh** (import
model — data loads on first refresh, expected), the model loaded all 3 tables
(Orders/People/Returns) + relationship + measure + DATEDIFF calc column, and **all
9 visuals rendered with real data**, bound to the compiler's own multi-table
entities (`Orders_ECFCA…`), not the flat spike model. `.twbx → unified .pbip
(TMDL model + PBIR visuals)` is now render-verified.

Two fixes were required to reach render (both grounded in `pbir_reference`, both
regression-tested): (1) the M partition path was double-escaped (`C:\\Users` →
`C:\Users`); (2) the `.pbip` pointer carried a `$schema` Power BI rejects — its
own output has none (removed; added `enableAutoRecovery`).

**Known, expected (not bugs):** (a) the "Sales by City/State" bubble maps scatter
to Europe/Africa — Bing geocoder resolving ambiguous US names abroad (the
documented geocoder-divergence finding); (b) dashboard **layout is rough**
(portrait canvas, spread-out visuals) — the zone→position translation is crude;
cosmetic only, data/bindings correct.

## V2 dashboard layout polish

**Root cause (from real numbers).** Tableau dashboard zones are **absolute** in a
0–100000 space (confirmed in-bounds for content); PBIR positions are pixels. The
scale and portrait aspect were already correct. The page looked scattered because
the old `layout.apply` did raw proportional placement + a blanket 120×90 min-size
clamp with **no de-overlap and no off-canvas handling**:
1. **off-canvas tooltip sheets** (parked at `x≈100000` in Tableau — "Sales by City
   - Tooltip", "Top Sold Products - Tooltip") were **clamped onto the canvas and
   stacked on top of each other**;
2. only 9 of ~24 worksheet zones are emitted, so content sat at true positions on
   an 1822-tall canvas with **giant empty bands** where skipped sheets used to be;
3. degenerate legend/KPI/header strips got inflated by the clamp and collided.

**The fix (`layout.py`, row-compaction — approved strategy).**
- **On-canvas test** rejects parked/tooltip zones (majority of the zone must fall
  within 0..100000); off-canvas emitted visuals → a tidy **overflow grid** at the
  bottom (not clamped into content).
- **Cluster into rows** by vertical proximity; within a row, order left→right and
  size widths **proportional to zone widths**; row height tracks the tallest zone.
- **Stack rows with uniform 16px padding**, deleting the empty bands → no giant
  gaps, and **no overlaps by construction**.
- Min-size floor + on-canvas clamp applied within the row model; page dimensions
  are **integers** (matching Power BI's own `page.json`). Deterministic.
- Auto-grid fallback (uniform tiles, even spacing) for pages with no geometry.

**Before → after (Superstore, `build-pbip`).**

| | before | after |
| - | - | - |
| Canvas | 1280×**1822** (sparse) | 1280×**1242** |
| Overlaps | tooltips stacked at (1160,0) | **none** (verified) |
| Max vertical gap | large empty bands | **16px** (row spacing) |
| Off-canvas tooltips | clamped into content | routed to overflow grid |
| Layout | scattered/cramped | 5 content rows + 2-tile overflow |

Bindings/data/coverage unchanged (still 9 emitted). Existing pipeline + model
emission untouched. **78 tests pass** (3 new layout tests: overlap-free, row
clustering, off-canvas overflow, compacted height, determinism, auto-grid), ruff
clean.

**Zone types not placed as content (with reason):** off-canvas **tooltip
worksheets** (Tableau parks them at `x≈100000`) — routed to the overflow grid, not
the main flow. (Note: a color-legend and a header sparkline are still *emitted*
as visuals and placed as rows; re-classifying those is an emit-scope concern, not
layout.)

**Render-gate: PENDING (your anchor).** Steps in `docs/VISUAL.md` V2 render-gate,
plus for this layout specifically: rebuild `tab2pbi build-pbip`, open
`data/pbip/Superstore.pbip`, and confirm the page now looks **clean** — visuals
sensibly sized, rows roughly matching the dashboard's top-to-bottom /
left-to-right arrangement, **no giant empty gaps, no overlaps**. Pixel-perfect
parity is *not* the goal (different layout engines) — "clean and recognizably
faithful" is.

**V2 next steps (ranked):** (1) **run the layout render-gate**; (2) broader mark
coverage + cross-table visuals; (3) n>1 workbook corpus; (4) prior-art search,
then fold both compilers into the paper.

## Demo app (self-service web app)

**What was built** — additive `demo/` web app; the compiler is **untouched**
(existing **78 tests still pass**, ruff clean). Replaces the old CLI walkthrough
(`run.sh`/`run.ps1`/`screenshots/` removed; a "CLI alternative" note folded into
the new `demo/README.md`).

- **Backend** `demo/backend/` (FastAPI, pinned): `POST /api/convert` (validates a
  `.twbx` = zip w/ `.twb` + `.hyper`, 50 MB cap, runs `build_pbip.run` in an
  isolated temp dir, returns the combined report + a 30-min download token),
  `GET /api/download/{token}` (portable zip), `GET /api/health`. Clean JSON
  errors (no stack traces), CORS for the dev frontend, TTL temp-dir cleanup.
- **Frontend** `demo/frontend/` (React + Vite + Tailwind, pinned, no runtime
  CDN): drag-and-drop upload with empty/loading states; a report view (model +
  visual coverage, emitted-by-type, skipped-by-taxonomy with reasons) carrying
  the honest labels (coverage %, "NOT render-verified", geocoder caveat); a
  prominent Download + "How to open" panel; light/dark, responsive.

**Portability decision (the critical one) + limitation.** The compiler writes an
**absolute** `File.Contents` CSV path in TMDL — a downloaded `.pbip` would open
empty elsewhere. Fixed in a **demo-side packager** (`packaging.py`, compiler
untouched): the download **bundles the per-table CSVs** and rewrites partitions
to `File.Contents(DataFolder & "\table.csv")` using a Power BI **`DataFolder`
query parameter** (+ `expressions.tmdl`, + a `ref` in `model.tmdl`).
**Limitation (documented in UI + `demo/README.md`):** the user must set
`DataFolder` to the extracted `data` folder and Refresh once. If unset, the model
raises a **clear error** on refresh — it **never silently loads empty**.
(Rejected: inline base64 embed — silent-empty risk if the deflate format is off;
local-only absolute path — opens empty for anyone else.)

**What works (verified via `starlette.TestClient`):** upload Superstore → 200
with the full report (3 tables, 1 measure, 9 visuals, coverage) → download a
484 KB zip containing `.pbip` + `.SemanticModel` + `.Report` + `data/*.csv` +
parameterized partitions + `expressions.tmdl`. Frontend `npm run build`
(tsc + vite) passes. **CI:** added a backend-pytest step + ruff on `demo/backend`
+ a Node job that builds the frontend. Main `pytest` unchanged (still 78).

**Demo-gate: PENDING (your anchor).** Structure-valid ≠ renders. Steps:
1. `pip install -e . && pip install -r demo/backend/requirements.txt` then
   `uvicorn demo.backend.app:app --reload --port 8000`.
2. `cd demo/frontend && npm install && npm run dev` → open <http://localhost:5173>.
3. Drop `examples/Superstore.twbx`, read the report, click **Download .pbip**.
4. Unzip, open the `.pbip` in Power BI Desktop, set the `DataFolder` parameter to
   the extracted `data` folder, **Refresh** — confirm model + visuals load/render.
5. **Portability proof:** move the extracted folder somewhere else, re-point
   `DataFolder`, Refresh — confirm it still loads (path isn't hard-coded).

**Decisions I made (unspecified):** `DataFolder` default is an obvious
placeholder (errors loudly if unset, never silent-empty); download tokens are
30-min TTL with lazy temp-dir purge; project name derived from the uploaded
filename (sanitized); backend imports the compiler from `src/` (no install needed
for local dev, though `pip install -e .` is cleaner).

**Demo next steps (ranked):** (1) **run the demo-gate**; (2) public hosting
(container the backend + static frontend; note the Hyper API + Power BI Desktop
constraints); (3) show a small live preview of the emitted page layout; (4) fold
into the paper as the artifact's front door.

## Coverage improvements (build the buildable, keep the impossible honest)

Additive; already-converted items unchanged; **87 main + 11 backend tests pass**,
ruff clean. Every new conversion is tied to a test.

### Triage (Superstore)
- **Buildable → built (4):** conditional aggregation `Calc_1069` (YoY%); calc→calc
  `% Diff Shape`; the real `Sales by State - Map`; two order-detail tables.
- **Impossible → kept as labeled skips:** table calcs (`RANK_UNIQUE`, `Index`),
  window fns (`WINDOW_MAX/MIN`), custom-geometry map (`Sales by Region`), Gantt,
  custom-shape design marks (11), `empty_formula` group, `ATTR`/`DATEPARSE`/
  SI-unit string-formatting measures, and the `dual_axis` sheet (uses Measure
  Values — converting would drop measures).
- **Deferred to workbook #2** (can't validate on Superstore): LOD→`CALCULATE`
  (no `{FIXED}` here), `dual_axis`→combo (Superstore's case is Measure Values),
  and the general `STR`→`FORMAT` / `DATEPART`→`YEAR` building blocks.

### Converters added (one logical change each + test)
| Converter | File | What | Test |
| --------- | ---- | ---- | ---- |
| Parameter inlining | `ir/context.py` | a field naming a constant param → its value (`Parameter 1`→`2022`) | `test_coverage::test_parameter_inlined_conditional_aggregation` |
| Conditional aggregation (SUMX) | `rewrite/dax.py` | `SUM(<row expr>)` → `SUMX(table, …)` w/ `ZN`→`COALESCE(.,0)` | `test_transpiler::test_aggregation_over_expression_becomes_sumx` |
| Calc-to-calc reference | `rewrite/dax.py` (2nd pass) | field → `[measure]` **iff** the dependency converted; else keep skip | `test_coverage::test_calc_to_calc_reference` / `…_only_if_dependency_converts` |
| Measure-ref DAX | `rewrite/dax.py`, `ir/ast_utils.py` | `measure_ref` node → `[Name]` | `test_transpiler::test_measure_ref_dax` |
| Geo gate fix | `visual/extract.py` | geographic = map mark **or** geometry encoding (not any State/City dim); generated geometry alone isn't a skip | `test_visual_mapping::test_generated_geometry_with_standard_dim_emits_map` |
| Dims-only detail table | `visual/mapping.py` | Text with ≥2 dims, 0 measures → `tableEx` | `test_visual_mapping::test_dims_only_text_is_detail_table` |
| Proxy evaluator (row engine) | `evaluation.py` | evaluate conditional/SUMX row-wise so YoY is proxy-checked | `test_evaluation::test_conditional_aggregation_sumx` |

### Before → after (Superstore)
| | before | after |
| - | - | - |
| **Model** measures | 1 | **3** (`Profit/Sales`, YoY `Calc_1069`, `% Diff Shape`) |
| Model coverage (measures+cols/total) | 11.8% | **23.5%** |
| Model skips | 11 | **9** |
| **Proxy-correctness** | 1/1 | **2/2** (YoY now evaluable + matches) |
| **Engine-verified** | 1/1 | **1/1** (YoY `powerbi_value` pending your check) |
| **Visual** emitted | 9 | **11** |
| Visual coverage | 28.1% | **34.4%** |
| Visual skips | 23 | **21** |

**Correctness discipline held:** the geo fix also **corrected two previously
mis-emitted maps** — `Map - Color Legend` (a legend) and `Sales by City - Tooltip`
were wrongly bubble maps; they're now a labeled skip and a column chart, and the
*real* `Sales by State - Map` emits. This changes which items emit (net +2) but
removes plausible-but-wrong output — flagged, not hidden.

### ⚠️ You must engine-verify (in Power BI)
1. **YoY `[Calculation_1069…]`** — proxy value **0.2036** is in
   `examples/eval/ground_truth_superstore.csv` as a stand-in; **replace with the
   real Tableau value and fill `powerbi_value`** (`--tolerance 1e-3`). Note it
   **inlines Parameter 1 = 2022** (a faithful snapshot; a What-If parameter is the
   interactive target).
2. **`% Diff Shape`** — returns **text**, so it's **not numerically
   proxy-checkable**; eyeball it in Power BI (`SWITCH(TRUE(), [YoY] > 0,
   "Positive", …)`).
3. **The 3 new visuals** (State map + 2 detail tables) and the 2 reclassified ones
   — confirm in the render-gate (`docs/VISUAL.md`).

**Coverage next steps (ranked):** (1) **build the LOD→`CALCULATE` converter and
validate on a 2nd workbook** (with `{FIXED}`); (2) the `dual_axis`→combo + general
`STR`/`DATEPART` converters on that workbook; (3) then the **2–3 workbook corpus**;
(4) fold the higher numbers into the paper.

## Ranked next steps

1. **Build a 2–3 workbook corpus (move past n=1).** Every paper number comes
   from one workbook. A small, license-checked corpus of workbooks that embed
   Hyper extracts is the single most important step for credibility — it turns
   the taxonomy and coverage discussion from anecdote into evidence.
2. **Resolve the paper's `[CITATION NEEDED]` items** (above), especially the
   §1 claim about existing tools and the `.bib` DOI/page verification.
3. **Decide + implement the `from_twb` merge.** Closes the one no-silent-drops
   gap in the relationship path (also a paper limitation).
4. **Conditional aggregations → CALCULATE/SUMX.** Biggest realistic coverage
   gain on real workbooks.
5. **Per-dimension evaluation** and **multi-measure engine verification** —
   strengthen the correctness story beyond a single grand-total anchor.
6. **String/date function breadth** (`STR`, `DATEPARSE`, `LOG`/`POWER`) — lower
   priority, high effort.
7. **Capture the demo screenshots** for Figure 1.
