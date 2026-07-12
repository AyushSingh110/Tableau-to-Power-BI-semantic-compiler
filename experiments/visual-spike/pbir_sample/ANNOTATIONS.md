# PBIR sample — field-by-field annotations

> **Provenance & honesty label.** The two `visual.json` **query blocks** below are
> transcribed from Microsoft's own PBIR authoring references
> (`microsoft/skills-for-fabric` → `.../references/cartesian.md` and `map.md`) and
> bound to the real entity/column names emitted by our compiler
> (`data/Model.json`). They are **schema-grounded drafts, NOT yet render-verified**
> — I (the assistant) cannot launch Power BI Desktop. The surrounding scaffolding
> files (`version.json`, `report.json`, `page.json`, `pages.json`,
> `definition.pbir`) use documented `$schema` URLs but their exact required-field
> sets/versions should be confirmed by opening the project in Desktop. See the
> repository docs cited in `../FEASIBILITY.md`.

The generated model exposes table `Orders_ECFCA1FB690A41FE803BC071773BA862` with
columns including `Category`, `State`, and `Sales` (source: `data/Model.json`).

## 1. `barSalesByCategory/visual.json` — column chart (Sales by Category)

| Field | Value | Meaning |
| ----- | ----- | ------- |
| `visual.visualType` | `columnChart` | stacked column chart (`clusteredColumnChart` for side-by-side). Source: `cartesian.md`. |
| `query.queryState.Category` | role bucket | the **axis** role. |
| `Category.projections[0].field.Column.Expression.SourceRef.Entity` | `Orders_…` | semantic-model **table** name (must match the dataset). |
| `…Column.Property` | `Category` | the **column** on that table. |
| `…queryRef` | `Orders_….Category` | fully-qualified query reference. |
| `…nativeQueryRef` | `Category` | UI display label. |
| `query.queryState.Y` | role bucket | the **value** role (column heights). |
| `Y.projections[0].field.Aggregation.Expression.Column…` | `Orders_….Sales` | the measure column. |
| `Aggregation.Function` | `0` | **0 = Sum** (Tableau `sum:Sales` → DAX/agg Sum). Source: `cartesian.md`. |
| `drillFilterOtherVisuals` | `true` | standard cross-filter default. |

Maps cleanly from the Tableau worksheet **"Sales by Category"**
(`rows = Category` dimension, `cols = sum:Sales`) — confirmed in `../marks_dump.json`.

## 2. `mapSalesByState/visual.json` — Azure Map (Sales by State)

| Field | Value | Meaning |
| ----- | ----- | ------- |
| `visual.visualType` | `azureMap` | the **recommended** map visual. `map`/`filledMap` are deprecated (`PBIR_VISUAL_TYPE_DEPRECATED`). Source: `map.md`. |
| `query.queryState.Category` | role bucket | the **Location** role — bind the geographic column here. |
| `Category.projections[0]…Property` | `State` | Azure Maps geocodes `State` automatically (no lat/lon needed). Source: `map.md`. |
| `query.queryState.Size` | role bucket | the **Size** role — bubble sizing by measure. |
| `Size.projections[0].field.Aggregation…Property` | `Sales`, `Function 0` | Sum of Sales, sizing the bubbles. |

Maps from the Tableau worksheet **"Sales by State - Map"** (Multipolygon mark,
`lod = State`, `color/size = Sales`) — confirmed in `../marks_dump.json`.

> ⚠️ **This is a bubble map, not a filled choropleth.** The Tableau original is a
> *filled* (Multipolygon) map. Azure Maps as documented here plots **bubbles**
> sized by `Sales`; the reference does **not** document choropleth
> (region-shading) via a role binding. See §3 and `../FEASIBILITY.md` for the
> honest map-translatability discussion.

## 3. The filled-choropleth gap (why there is no clean known-good sample)

A true "filled map by administrative region → Location binding" has **no clean,
recommended, documented PBIR target** today:

- **Legacy `filledMap`** *does* choropleth-shade admin regions via Bing, but is
  **deprecated** for new authoring (`PBIR_VISUAL_TYPE_DEPRECATED`). Its exact
  PBIR role keys are **not** transcribed here because I could not ground them in a
  current Microsoft doc — fabricating them would violate the no-guess rule. To get
  a known-good legacy sample, create a filled map manually in Power BI, save as
  `.pbip`, and reverse-document its `visual.json` (path B).
- **`azureMap`** is recommended but the authoring reference documents only bubble
  plotting; choropleth/region layers are not covered as a simple role binding.

**Geocoder-divergence caveat (applies to any Tableau→Power BI map).** Tableau uses
its own proprietary geocoder; Power BI/Azure Maps uses Azure/Bing. For standard
admin regions (US states) results are **semantically equivalent** but **not
point-identical** (boundary polygons, centroid placement, and ambiguous-name
resolution differ). Custom/"generated geometry" territories — e.g. the Tableau
worksheet **"Sales by Region"**, whose polygons are `Geometry (generated)` over a
non-standard `Region` grouping — have **no** geocoder equivalent and are **not
translatable** without shipping the polygon geometry itself.
