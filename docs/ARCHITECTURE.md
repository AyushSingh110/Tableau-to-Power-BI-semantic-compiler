# Architecture

`tab2pbi` is a deterministic, staged compiler from a Tableau workbook to a Power
BI Tabular Object Model (TOM), organized around a single canonical intermediate
representation (IR). This document specifies the IR, discusses the Tableau↔DAX
semantic mismatch that motivates it, and situates the work in the literature on
source-to-source transpilation, semantic data integration, and data provenance.

For the stage-by-stage flow and diagrams, see the **Architecture** section of
the [README](../README.md). This document is the deeper reference.

## 1. The intermediate representation

The IR is a plain, JSON-serializable object graph. It is engine-agnostic: it
describes *what* a model contains (tables, typed columns, measures as ASTs,
relationships) without committing to Tableau or DAX syntax.

### 1.1 Model

```
CanonicalModel
├── model_type          "flat_extract" | "relational_model"
├── tables              { name -> Table }
├── measures            { name -> DAX string }          (aggregation-bearing)
├── calculated_columns  [ { name, table, dax } ]        (row-level)
├── parameters          [ { name, table, dax, note } ]  (constant calcs)
├── measure_table_map   { measure -> owning table }
├── relationships       [ Relationship ]
├── provenance          { fact_table_inference, ast_builder, ... }
└── conversion_report   { counts, coverage_pct, failure_taxonomy, ... }

Table         { columns: [str], type: "fact" | "dimension" }
Relationship  { from_table, from_column, to_table, to_column,
                cardinality, cross_filter_direction, confidence }
```

The versioned JSON Schemas live in
[`src/tab2pbi/ir/schema/`](../src/tab2pbi/ir/schema/) and every run validates the
semantic model and the final model against them (`ir/validate.py`).

### 1.2 The measure AST

Each measure carries a typed AST — the object the transpiler walks to emit DAX
and the classifier inspects to decide convertibility. Node kinds:

| Node | Fields | Meaning |
| ---- | ------ | ------- |
| `constant` | `dtype`, `value` | numeric / string / boolean / null literal |
| `field` | `name`, `table?` | a field reference; `table` is filled by context resolution |
| `aggregation` | `agg`, `arg` | `SUM`/`AVG`/`COUNTD`/… of a sub-expression |
| `binary` | `op`, `left`, `right` | arithmetic / string operator |
| `comparison` | `op`, `left`, `right` | `=`, `<>`, `<`, `>`, `<=`, `>=` |
| `logical` | `op`, `left`, `right` | `AND` / `OR` |
| `not` / `unary` | `operand` | logical negation / unary minus |
| `conditional` | `branches[]`, `otherwise` | normalized `IF`/`CASE` |
| `function` | `name`, `args[]` | any other function call |
| `unsupported` | `reason` | recognized-but-not-modeled (e.g. LOD) |
| `parse_error` | `reason` | the parser could not handle the input |

`unsupported`/`parse_error` are first-class: an un-handled construct is a node
with a reason, never a dropped calculation.

### 1.3 Pipeline as IR transformations

Every stage is a pure-ish function reading and writing the IR (or its inputs):

1. **parse** → parsed metadata + physical schema + per-table data.
2. **semantic_model** → IR with measure ASTs and fact/dimension tags.
3. **context** → annotate `field` nodes with owning tables.
4. **rewrite** → walk ASTs, emit DAX; split into measures / columns / parameters
   / skipped-with-taxonomy.
5. **canonical + finalize** → assemble the model and the audit report.
6. **export** → TOM + Tabular Editor `Model.json`.

Because every transformation operates on the *same* structured object, each
un-handled construct surfaces once, with a reason, instead of being silently
mistranslated at string level.

## 2. The Tableau ↔ DAX semantic mismatch

Tableau and Power BI are different analytical engines; their calculation
languages encode different evaluation models. A faithful compiler must make
those differences explicit rather than assume they line up.

### 2.1 Context of evaluation

Tableau **table calculations** (`WINDOW_*`, `INDEX`, `RANK`, `RUNNING_*`,
`LOOKUP`) and **Level-of-Detail** expressions (`{FIXED …}`, `{INCLUDE …}`,
`{EXCLUDE …}`) are defined relative to a visualization's *addressing and
partitioning* — the rows/marks in the view. DAX measures instead evaluate in a
**filter context** and **row context** derived from the model and the report's
slicers, combined via `CALCULATE`. There is no general, context-free rewrite:
the same Tableau formula can mean different things in different views, and that
view context does not survive migration. `tab2pbi` therefore refuses to
translate these and records them under `table_calc` / `window_fn` /
`lod_expression` in the failure taxonomy.

### 2.2 Row-level vs aggregate

Tableau distinguishes row-level from aggregate calculations at *use* time. In a
tabular model this distinction is structural and must be decided at build time:
a row-level expression is a **calculated column**; an aggregate is a **measure**.
Emitting a row-level `DATEDIFF` as a measure yields invalid DAX. `tab2pbi`
splits by the presence of an aggregation node in the AST (see
`rewrite/dax.analyze`).

### 2.3 Relationships and identity

Tableau's logical layer can defer join resolution to query time; Power BI needs
**explicit relationships** with cardinality and cross-filter direction *before*
the model loads. And where Tableau identifies fields by caption (ambiguous
across data sources), DAX identifies columns as `Table[Column]`. The IR resolves
each field to an owning physical table so measures have an unambiguous home.

## 3. Related work

`tab2pbi` is a small **tool / systems contribution**: a deterministic,
provenance-preserving transpiler between two analytical engines. It draws on
three established lines of work.

### 3.1 Source-to-source transpilation and IR-based query translation

Translating between query/expression dialects via a typed IR is the standard
architecture in modern data tooling. **Apache Calcite** provides a relational
algebra IR and rule-based transformations across heterogeneous backends (Begoli,
Camacho-Rodríguez, Hyde, Mior, Lemire, *Apache Calcite: A Foundational Framework
for Optimized Query Processing Over Heterogeneous Data Sources*, SIGMOD 2018).
**sqlglot** (T. Mao, open-source) is a widely-used SQL parser/transpiler that
normalizes dialects through an expression AST — the same parse-into-IR,
transform, re-emit shape used here. The classic compiler framing of parsing,
typed intermediate forms, and code generation is Aho, Lam, Sethi & Ullman,
*Compilers: Principles, Techniques, and Tools* (2nd ed., 2006).

### 3.2 Semantic data integration

Mapping schemas and semantics across systems while preserving meaning is the
subject of data integration theory. See Lenzerini, *Data Integration: A
Theoretical Perspective* (PODS 2002) for the formal framing of mediated schemas
and mappings, and Halevy, Rajaraman & Ordille, *Data Integration: The Teenage
Years* (VLDB 2006) for a systems perspective. The IR here plays the role of a
mediated model between the Tableau and Power BI "sources".

### 3.3 Data provenance

The project's "no silent drops / always a reason" policy is an application of
provenance: every output measure, skipped calculation, and inferred relationship
records *why* and *from what* it was produced. For the foundations of why/how/
where provenance see Cheney, Chiticariu & Tan, *Provenance in Databases: Why,
How, and Where* (Foundations and Trends in Databases, 2009), and Buneman, Khanna
& Tan, *Why and Where: A Characterization of Data Provenance* (ICDT 2001).

## 4. Known architectural gaps

- **Declared TWB relationships are not merged** into the canonical model (only
  data-driven ones reach the TOM). See the README stage guarantee.
- **Conditional aggregations** (`SUM(IF … )`) and **parameter-dependent**
  measures are not yet transpiled (candidate: `CALCULATE`/`SUMX` with inlined
  parameters).
- The evaluator compares **grand totals only**; per-dimension equivalence is a
  TODO (see [EVALUATION.md](EVALUATION.md)).
