# tab2pbi — The Project Explained (Interview & Revision Guide)

> A plain-English walkthrough of what this project is, how it works, what was
> built, what it achieves, and how to talk about it. Written to be revised the
> night before an interview.

---

## 1. The 30-second pitch (memorize this)

> "I built **tab2pbi**, a compiler that translates Tableau workbooks into Power BI.
> Instead of trying to recreate the dashboard visually, it treats both tools as
> *analytical engines* and preserves the **meaning** of the analysis — the
> measures, relationships, and charts. The key idea is **honesty**: when it can't
> translate something correctly, it doesn't guess or silently drop it — it reports
> exactly what and why, in a machine-readable failure report. I verified the
> output against the real Power BI engine, and wrapped it in a web app where you
> upload a Tableau file and download a working Power BI file."

**Why this is impressive:** it's a real *compiler* (not regex scripts), it's
*verified* against the actual engine, it's *honest* about its limits, and it has
tests, CI, docs, and a demo. That combination is rare in a portfolio project.

---

## 2. The problem (why this is hard)

Tableau and Power BI both let you analyze data, but they store and compute things
very differently:

| Tableau | Power BI | Why translation is hard |
| --- | --- | --- |
| **LOD expressions** (`{FIXED …}`), **table calcs** | **DAX** with filter/row context | The same formula *means* different things depending on the visual it sits in. |
| A field is **row-level or aggregated depending on where you use it** | You must decide **at build time**: is it a *measure* or a *calculated column*? | Put a row-level formula in a measure slot → invalid DAX. |
| **Joins resolved at query time** (deferred) | **Relationships with explicit direction & cardinality** | Cardinality must be decided *before* the model loads. |
| A field is identified by its **caption/name** | A field is `Table[Column]` | A measure needs to know exactly which table it belongs to. |

Most existing "converters" hide these gaps — they recreate the dashboard's *look*
and quietly approximate or drop the calculations that carry the real meaning. This
project does the opposite: **get the analysis right, and be explicit about
whatever can't be translated.**

---

## 3. What was built (the big picture)

There are **three parts**:

1. **Data-model compiler** — turns the Tableau data model (fields, calculations,
   relationships) into a Power BI **semantic model** (tables, measures,
   relationships).
2. **Visual compiler** — turns Tableau worksheets/dashboards into Power BI
   **report visuals** (charts, maps).
3. **End-to-end pipeline + demo** — one command (`build-pbip`) produces a complete
   Power BI project file (`.pbip`) that opens in Power BI Desktop, plus a web app
   where anyone can upload a `.twbx` and download the result.

Everything is built around **one central idea: a canonical Intermediate
Representation (IR)** — a neutral, tool-agnostic model that sits *between* Tableau
and Power BI. Tableau → IR → Power BI. This is exactly how real programming-language
compilers work (source code → IR → machine code).

---

## 4. Key concepts explained simply

You'll be asked about these — here they are in plain English:

- **Compiler** — a program that translates one language/format into another while
  preserving meaning. Here: Tableau's model → Power BI's model.

- **Intermediate Representation (IR)** — a neutral "middle" format. Instead of
  writing Tableau→PowerBI directly (messy), we do Tableau→IR then IR→PowerBI. The
  IR is where all the real logic lives, and it makes the system easy to test and
  extend.

- **AST (Abstract Syntax Tree)** — when we read a Tableau formula like
  `SUM([Profit]) / SUM([Sales])`, we turn it into a *tree* structure (a "divide"
  node with two "sum" children). Trees are easy for a program to understand and
  transform, unlike raw text.

- **Tokenizer + Parser** — the tokenizer chops a formula into pieces (words,
  numbers, brackets, operators); the parser assembles those pieces into the AST.
  I used a **Pratt parser**, a clean technique for handling operator precedence
  (so `a + b * c` groups correctly).

- **Transpiler** — the part that walks the AST and writes out **DAX** (Power BI's
  formula language). It only writes DAX for things it *knows* are correct;
  everything else is reported as "skipped, with a reason."

- **Measure vs. Calculated Column** — a **measure** is an aggregation (one number
  over a filter, like a ratio); a **calculated column** is computed row-by-row
  (like days between two dates). The compiler detects which one a formula is (does
  it contain an aggregation?) and places it correctly — a key correctness detail.

- **TOM / TMDL** — the Power BI **data model** format. TOM is the JSON version;
  TMDL is the newer text version that Power BI Desktop's project format uses.

- **PBIR** — the Power BI **report** format: one JSON file per visual
  (`visual.json`) describing the chart type and which fields go where.

- **.pbip** — a Power BI *Project*: a folder containing the model (TMDL) + the
  report (PBIR). This is what we generate and what opens in Power BI Desktop.

- **Failure taxonomy** — a fixed set of labeled "reasons for skipping"
  (`table_calc`, `window_fn`, `custom_geometry`, etc.) so every un-translated
  thing is categorized and counted, never silently lost.

---

## 5. The architecture (walk through this diagram in the interview)

```
   Tableau .twbx file
          │
          ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  PARSE                                                        │
 │  • parse/tableau_xml → read fields, calcs, filters, params   │
 │  • parse/hyper       → read the .hyper data extract (schema  │
 │                        + sample data) via official Hyper API │
 │  • parse/mapping     → match logical fields to physical cols │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  BUILD THE IR (the neutral middle model)                     │
 │  • ir/tokenizer + ir/parser → turn each calc into an AST     │
 │  • ir/semantic_model        → assemble tables/columns/calcs  │
 │  • ir/context               → work out which table each      │
 │                               measure belongs to             │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  TRANSLATE + DECIDE                                           │
 │  • rewrite/dax        → AST → DAX (only what's safe)         │
 │  • classify/classifier→ label each calc convertible or not  │
 │  • relationships/from_hyper → infer foreign keys FROM DATA   │
 │                               (uniqueness + coverage checks) │
 │  • relationships/from_twb   → read declared joins (audited)  │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  ASSEMBLE + EXPORT                                            │
 │  • ir/canonical + ir/finalize → one model + full audit report│
 │  • export/tom      → Power BI TOM (JSON model)               │
 │  • export/tmdl     → TMDL model (for the .pbip project)      │
 │  • visual/*        → PBIR report visuals (charts/maps)       │
 │  • build_pbip      → bundle model + visuals into one .pbip   │
 └─────────────────────────────────────────────────────────────┘
          │
          ▼
   Power BI .pbip  →  opens in Power BI Desktop
```

**Two things make this design good, and you should say them out loud:**

1. **Everything goes through the IR**, so Tableau-specific and Power BI-specific
   code never touch each other directly. That's what makes it testable and
   extendable.
2. **Every stage writes an auditable JSON file** and is **deterministic** (same
   input → same output). You can inspect exactly what happened at each step.

---

## 6. How the visual compiler works (the second half)

1. **Extract marks** — read each Tableau worksheet's *mark type* (bar, line, pie,
   map…) and its *shelves* (what field is on color, size, rows, columns).
2. **Map to a Power BI visual** — a deterministic table: Tableau `bar` →
   `columnChart`, `line` → `lineChart`, geographic field → `map`, etc. Anything
   with no clean target → **skipped with a reason** (e.g. custom-shape design
   marks, Gantt charts).
3. **Bind to the real model** — each chart field is wired to the correct table in
   the generated model (e.g. `Orders_…[Sales]`), so the visuals and the data model
   are one coherent whole.
4. **Lay out the page** — translate Tableau dashboard zone positions into Power BI
   canvas positions.
5. **Emit `visual.json`** — grounded in **Power BI's own real output** (I saved a
   reference `.pbip` that Power BI itself produced, and matched its exact format
   rather than guessing).

---

## 7. How correctness was verified (this is your strongest talking point)

I report **two separate numbers** and never mix them up:

- **Proxy correctness** — I re-compute the translated formula using a small Python
  evaluator and compare to Tableau's value. This checks that my *parser understood
  the formula*. (Result: 1/1.)
- **Engine-verified correctness** — I loaded the generated model into **Power BI
  Desktop** and compared Power BI's *actual* computed value to Tableau's. This
  checks the *real generated DAX*. (Result: 1/1 — Power BI `0.1247` vs Tableau
  `0.1246721724`.)

**Why report two numbers?** Because the proxy could be right for the wrong reasons
(my evaluator and my DAX generator share the same AST, so a shared mistake would
pass both). Only running it in the real engine proves the DAX is correct. I even
documented this as a "threat to validity" and used an honest tolerance (1e-3,
because I hand-read the value to 4 decimals off a card). **That level of honesty is
what separates real engineering from a demo.**

I also **render-verified the whole `.pbip`**: opened it in Power BI Desktop and
confirmed all 3 tables loaded and all 9 visuals drew real data.

---

## 8. What it achieves (the numbers, on the Superstore workbook)

**Data model:** 3 tables (Orders, People, Returns), 1 measure, 1 calculated column,
~4 parameters, 1 data-driven relationship. Model coverage 11.8%. **Engine-verified
correctness 1/1.**

**Visuals:** 32 worksheets → **9 emitted** (4 column charts, 2 maps, 1 area, 1 pie,
1 line), 23 skipped — each with a labeled reason. Visual coverage 28.1%,
**render-verified in Power BI Desktop.**

**Engineering:** ~40 Python modules in a clean package, **78 automated tests**,
GitHub Actions CI (tests + lint), versioned JSON-Schema validation, full docs, and
a full-stack web demo.

> **On the low coverage — say this confidently:** "The numbers are low *on
> purpose*. The sample workbook is dominated by table calculations, window
> functions, and custom-shape design marks that are genuinely impossible to
> translate faithfully. I'd rather report an honest 12% than a fake 90% with
> silent errors. Everything I *do* emit is verified correct."

---

## 9. The technology used (and why)

| Tech | Where | Why |
| --- | --- | --- |
| **Python** | The whole compiler | Great for parsing, data, and the Tableau Hyper API. |
| **Tableau Hyper API** | `parse/hyper` | Official way to read Tableau's `.hyper` data extract. |
| **Custom tokenizer + Pratt parser** | `ir/` | Proper parsing of Tableau formulas into an AST — no regex hacks. |
| **pandas** | data-driven relationship inference, proxy eval | Column profiling (uniqueness, coverage) and computing check values. |
| **JSON Schema** | `ir/validate.py` | Validates every stage's output — fail loudly on malformed data. |
| **pytest + ruff + GitHub Actions** | tests + CI | Automated testing and linting on every push. |
| **TMDL / PBIR / .pbip** | `export/`, `visual/` | The real Power BI project formats, matched against Power BI's own output. |
| **FastAPI** | `demo/backend` | Python web API that runs the compiler on an uploaded file. |
| **React + TypeScript + Tailwind + Vite** | `demo/frontend` | Modern, clean UI: upload → see report → download. |

---

## 10. The demo (how to show it)

- A user opens the web app, **drags in a `.twbx` file**.
- The **FastAPI backend** runs the full compiler and returns a **conversion report**
  (what converted, what was skipped and why, coverage %).
- The **React frontend** shows the report clearly, and gives a **Download button**
  for the generated Power BI `.pbip`.
- The user opens the `.pbip` in **Power BI Desktop**, clicks Refresh, and sees the
  model + charts.

This turns the whole project into something a non-technical person can *try*.

---

## 11. Weaknesses & what I'd do next (be honest — interviewers love this)

See the companion section in `HANDOFF_REPORT.md`; the short version:

1. **Tested on one workbook (n=1)** — the biggest limitation. Next: run 2–3 more
   public workbooks and report aggregate numbers.
2. **Coverage is modest** — many Tableau features (LOD, table calcs, custom
   maps/shapes) aren't translated. Some are genuinely impossible; others (like
   LOD → `CALCULATE`) are future work.
3. **Correctness anchored on 1 measure** — next: hand-verify more measures across
   workbooks.
4. **Dashboard layout is rough** — visuals are placed crudely; needs polish.
5. **Maps aren't pixel-faithful** — Power BI's geocoder differs from Tableau's, and
   filled/choropleth maps have no clean Power BI target. Documented, not hidden.
6. **Declared Tableau relationships are read but not merged** into the model yet.
7. **The demo is local-only** — hosting it publicly is a separate, bigger step.

---

## 12. Likely interview questions + short answers

**"What's the hardest part?"**
> Deciding *measure vs calculated column* correctly, and knowing which table a
> measure belongs to. Get either wrong and Power BI rejects the DAX. That's what
> the IR + context-resolution stage exists to solve.

**"Why an IR instead of translating directly?"**
> Direct translation tangles Tableau and Power BI logic together. An IR decouples
> them, so each side is simple, testable, and independently extendable — same
> reason real compilers use one.

**"How do you know the output is correct?"**
> Two numbers: a proxy check (parser understood the formula) and an engine-verified
> check (ran the real DAX in Power BI and matched Tableau's value). I keep them
> separate and I'm explicit that only the engine-verified one proves the DAX.

**"Why is coverage only ~12%?"**
> The sample workbook is deliberately hard — mostly table calcs and custom design
> marks that can't be faithfully translated. I report an honest number and skip
> the rest *with reasons*, rather than emitting plausible-but-wrong output.

**"What makes this different from existing converters?"**
> It's open, it's a real compiler with a typed IR, it verifies against the actual
> engine, and it never silently drops or fakes anything — every gap is reported in
> a machine-readable taxonomy.

**"How is it engineered?"**
> Clean Python package (~40 modules), 78 tests, CI with lint, JSON-Schema
> validation of every stage, deterministic outputs, full docs, and a FastAPI +
> React demo.

---

## 13. One-line summary for your resume

> **tab2pbi** — a semantic compiler that translates Tableau workbooks into Power BI
> (data model + report visuals) through a typed intermediate representation, with
> engine-verified DAX, a no-silent-drop failure taxonomy, 78 tests + CI, and a
> FastAPI/React demo.
