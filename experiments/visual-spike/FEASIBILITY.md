# Visual Compiler Feasibility Spike (Phase V0)

**Question:** can we build a *visual/report* compiler on top of the existing
`tab2pbi` *data-model* compiler, emitting Power BI **PBIR** (`.pbip`, documented,
open, per-visual `visual.json`) — not the legacy undocumented `.pbix` Layout blob?

**Recommendation up front: QUALIFIED GO.** Core cartesian charts and cards are
straightforwardly authorable in documented PBIR (proven below). Faithful **map**
translation is a **partial NO-GO** (deprecated targets, choropleth gap, geocoder
divergence) and should be handled with the same honest "report, don't fake"
stance as the data-model compiler. Details and effort below.

This spike is isolated under `experiments/visual-spike/`; it does not touch or
import `src/tab2pbi`.

---

## 1. What the Tableau source actually contains (real counts)

From `python experiments/visual-spike/dump_marks.py` → `marks_dump.json`
(workbook: `examples/Superstore.twbx`, *"Sample Superstore – Sales Performance /
VOTD"*):

- **32 worksheets.**
- **Mark types** (number of worksheets containing each):

  | Mark | Worksheets | Likely PBIR target |
  | ---- | ---------- | ------------------ |
  | `Shape` | 11 | partial (custom shape encoding) |
  | `Text` | 9 | `card` / `tableEx` / `matrix` |
  | `Bar` | 5 | `columnChart` / `barChart` |
  | `Line` | 3 | `lineChart` |
  | `Pie` | 3 | `pieChart` / `donutChart` |
  | `Automatic` | 3 | depends on encodings (ambiguous) |
  | `Area` | 2 | `areaChart` |
  | `Multipolygon` | 2 | **map (hard — see §3)** |
  | `Circle` | 1 | `scatterChart` |
  | `GanttBar` | 1 | no core visual (custom) |

- **Geographic worksheets: 4** — `Sales by State - Map`, `Sales by Region`,
  `Map - Color Legend`, `Top Sales by State - KPI`. Two carry real filled
  (`Multipolygon`) marks. `Sales by State - Map` binds `State` + `Sales`
  (both resolve to `Orders_…[State]`/`[Sales]`); `Sales by Region` uses
  **`Geometry (generated)`** over a non-standard `Region` grouping — a custom
  territory with no geocoder equivalent.

**Read of the vocabulary:** the *easy* majority is cartesian + text (Bar/Line/
Area/Pie/Circle/Text ≈ core charts + cards). The *hard* minority is real and
prominent in this showcase workbook: **11 shape-mark worksheets** (KPI/design
shapes) and **2 filled-map worksheets**. A faithful 1:1 port of *this specific*
VOTD dashboard is therefore genuinely partial; a compiler targeting core charts
covers most analytical worksheets but not the design-heavy ones.

## 2. Is programmatic PBIR emission viable? — Yes (evidence)

PBIR is a **publicly documented, open** format (unlike the legacy `.pbix`
Layout). Each page/visual is its own JSON file with a public JSON schema
[MS-Learn-PBIR]. We hand-authored a minimal working project as evidence:

- `pbir_sample/Superstore.Report/definition/pages/page1/visuals/barSalesByCategory/visual.json`
  — a `columnChart` (Category × Sum(Sales)).
- `pbir_sample/.../visuals/mapSalesByState/visual.json`
  — an `azureMap` (State as Location × Sum(Sales)).

Both `visual.json` **query blocks are transcribed from Microsoft's own PBIR
authoring reference** [MS-skills-fabric] and bound to the real entity/column
names our compiler emits (`Orders_ECFCA1FB690A41FE803BC071773BA862`,
`Category`/`State`/`Sales` from `data/Model.json`). All eight project JSON files
parse. Field-by-field provenance is in `pbir_sample/ANNOTATIONS.md`.

> **Honesty label:** these are **schema-grounded drafts, not render-verified** —
> the assistant cannot launch Power BI Desktop. `pbir_sample/README.md` gives the
> exact one-time preview-feature enablement and the open/verify steps for the
> human. The query structures (roles `Category`/`Y` for columnChart; `Category`/
> `Size` for azureMap; `Aggregation.Function: 0` = Sum) come from a real MS doc,
> so the risk is in scaffolding minutiae (exact `version` strings / required
> fields), not the visual query model.

**Conclusion:** authoring `visual.json` programmatically is clearly viable for
core visuals — the structure is regular (visualType + role buckets +
projections) and directly generable from a Visual IR.

## 3. Draft mark → visual mapping, and the honest untranslatable list

### Mapping (for marks actually found)

| Tableau mark + shelves | PBIR `visualType` | Field wells (roles) | Confidence |
| ---------------------- | ----------------- | ------------------- | ---------- |
| `Bar` (dim on one axis, measure on other) | `columnChart` / `barChart` | `Category`, `Y` (+`Series`=color) | High |
| `Line` (measure over date/dim) | `lineChart` | `Category`, `Y`, `Series` | High |
| `Area` | `areaChart` | `Category`, `Y`, `Series` | High |
| `Pie` | `pieChart` / `donutChart` | `Category` (legend), `Y` (values) | High |
| `Circle` (two measures) | `scatterChart` | `X`, `Y`, `Details` | Medium |
| `Text` (single value) | `card` | `Values` | High |
| `Text` (dims × measures grid) | `tableEx` / `matrix` | `Rows`, `Columns`, `Values` | Medium |
| `Multipolygon`/geo point by admin region | `azureMap` (bubble) | `Category`=Location, `Size` | Medium (bubble ≠ filled) |
| `Shape` (custom shape palette) | `scatterChart` w/ markers, or none | partial | Low |
| `Automatic` | inferred from encodings | — | Low (context-dependent) |
| `GanttBar` | — (no core visual) | — | **None** |

### Honest untranslatable / hard list (maps especially)

- **Filled choropleth by admin region** — *no clean modern target.* Legacy
  `filledMap` shades regions but is **deprecated** (`PBIR_VISUAL_TYPE_DEPRECATED`)
  [MS-skills-fabric]; the recommended `azureMap` is documented only for **bubble**
  plotting, not role-bound region shading. Our sample therefore ships an azureMap
  *bubble* approximation, and we explicitly do **not** claim a faithful choropleth.
- **Custom / "generated geometry" territories** — e.g. `Sales by Region`
  (`Geometry (generated)` over a non-standard `Region`). No geocoder equivalent;
  untranslatable without shipping the polygon geometry itself.
- **Dual-axis maps, background-image maps, density/heat maps** — no core PBIR
  role-binding equivalent.
- **`GanttBar`** — requires an AppSource/custom visual; not a core type.
- **Custom `Shape` encodings** (shape palettes / KPI iconography) — 11 worksheets
  here; only partially expressible.
- **Geocoder-divergence caveat (all maps).** Tableau's proprietary geocoder vs
  Azure/Bing differ in boundary polygons, centroids, and ambiguous-name
  resolution. Even the translatable cases (US `State`) will be **semantically
  right but not point-identical**.

## 4. Estimated effort for a real Visual IR + PBIR emitter (V1–V5)

Rough estimates (person-weeks), **not measured** — a spike sizing, not a schedule:

| Phase | Scope | Est. |
| ----- | ----- | ---- |
| **V1** | Formalize a Visual IR + marks extractor (per-worksheet mark + encodings → typed VisualNode; reuse existing field resolution). | 1–1.5 wk |
| **V2** | PBIR emitter skeleton (report/version/page scaffolding + `columnChart`) rendering end-to-end in Desktop; pin schema versions. | 1–2 wk |
| **V3** | Core cartesian + card coverage (bar/line/area/pie/scatter/card/matrix) + role & aggregation mapping. | 2–3 wk |
| **V4** | Maps: `azureMap` bubble + geocoder caveats + **honest skip** for choropleth/custom geometry/gantt/shape. | 2–3 wk (high uncertainty) |
| **V5** | Layout/position/formatting, dashboards→pages, filters, tests, schema-version hardening. | 3–4 wk |

**Total ≈ 9–14 person-weeks** to a credible V1 covering core charts, with maps
partial-and-honest.

### Top 3 risks

1. **PBIR preview/schema instability.** PBIR is explicitly *preview*; schema
   versions "expected to change," and GA will make PBIR mandatory but may shift
   shapes [MS-Learn-PBIR]. An emitter can break on Desktop updates → must pin and
   test `$schema` versions.
2. **Map translatability.** Filled choropleth has no clean recommended target;
   deprecated `filledMap`, undocumented azureMap region layers, geocoder
   divergence, and impossible custom geometry. Maps are ~4/32 worksheets here and
   visually central.
3. **No headless render verification.** There is no CI-able PBIR renderer; every
   visual type must be hand-verified in Desktop (as in this spike). Visual
   correctness cannot be gated the way the data-model compiler's output is.

## 5. GO / NO-GO

**QUALIFIED GO.**

- **GO** for a V1 that targets **core cartesian charts + cards** (bar/line/area/
  pie/scatter/card, and text-grids→matrix). PBIR emission for these is
  demonstrably viable (§2), the mapping is high-confidence (§3), and they cover
  the majority of *analytical* worksheets.
- **NO-GO (carve-out)** on promising **faithful map translation**. Deliver an
  azureMap **bubble approximation** plus an **explicit, taxonomy-reported skip**
  for choropleth / custom-geometry / dual-axis / density maps and `GanttBar` /
  custom `Shape` design marks — mirroring the data-model compiler's
  "no-silent-drop" ethos. Do **not** market visual parity for design-heavy
  dashboards like this VOTD workbook.

**Reasoning.** The format is open and documented, the query model is regular and
generable, and we produced grounded sample visuals. The honest limiter is not the
format but the *vocabulary*: maps and custom design marks are genuinely hard or
impossible to port faithfully, and the tool's credibility depends on saying so
rather than emitting plausible-but-wrong visuals. A visual compiler that ports
core charts and *reports* the rest is a real, shippable contribution consistent
with the project's stance.

## 6. V1 Visual IR — one-paragraph sketch (for the next prompt)

Introduce a `VisualNode { worksheet, markType, visualType (mapped or None),
wells: { role -> [FieldRef{ table, column, aggregation }] }, unmapped_encodings,
skip_reason? }`, produced by a marks extractor that reuses the existing
logical→physical field resolution, and a `PageNode` that groups VisualNodes
(dashboards → pages). A single deterministic `mark → (visualType, role-map)`
table drives translation; any mark/encoding with no mapping yields a
`VisualNode` with a `skip_reason` recorded in a **visual failure taxonomy**
(`unsupported_mark`, `map_choropleth`, `custom_geometry`, `custom_shape`,
`gantt`, `dual_axis`, …), exactly mirroring the data-model compiler's conversion
report. The PBIR emitter walks `PageNode`s and writes `definition/pages/**/
visual.json` from the role-map, pinning `$schema` versions and validating each
file against the public PBIR schemas before Desktop ever opens the project.

---

## Sources

- **[MS-Learn-PBIR]** Microsoft Learn, *Power BI Desktop project report folder*
  (PBIR/PBIP structure, `definition/` folder, public schemas, preview status):
  <https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-report>
- **[MS-skills-fabric]** Microsoft `skills-for-fabric`, PBIR report-authoring
  references — `cartesian.md` (columnChart roles + aggregation) and `map.md`
  (`azureMap` roles; `map`/`filledMap` deprecation `PBIR_VISUAL_TYPE_DEPRECATED`):
  <https://github.com/microsoft/skills-for-fabric/tree/main/plugins/powerbi-authoring/skills/powerbi-report-authoring/references>
- PBIR JSON schemas (public): <https://github.com/microsoft/json-schemas/tree/main/fabric/item/report/definition>
- Deneb PBIR Implementation Guide (surfaced during research; Deneb-specific, not
  used for standard-visual roles): <https://deneb.guide/docs/pbir-guide>
