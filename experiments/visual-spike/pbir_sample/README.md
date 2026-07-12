# PBIR sample — how to enable PBIP/PBIR and verify this project

> **Status: schema-grounded draft, NOT render-verified.** The assistant that
> authored this cannot run Power BI Desktop. Your one manual step is to open it
> and confirm/repair. See `ANNOTATIONS.md` for the field-by-field provenance.

## 1. Enable PBIP + PBIR in Power BI Desktop (one-time)

Source: Microsoft Learn, *Power BI Desktop project report folder*
(`learn.microsoft.com/power-bi/developer/projects/projects-report`).

1. **File → Options and settings → Options → Preview features.**
2. Enable **"Power BI Project (.pbip) save option"**.
3. Enable **"Store reports using enhanced metadata format (PBIR)"**.
4. Restart Power BI Desktop.

(PBIR is in **preview**; the enable text and behavior may change between Desktop
releases.)

## 2. What this project contains

```
Superstore.pbip                     ← project pointer
Superstore.Report/
  definition.pbir                   ← references a semantic model (byPath)
  definition/
    version.json  report.json
    pages/pages.json
    pages/page1/page.json
    pages/page1/visuals/
      barSalesByCategory/visual.json   ← columnChart: Category × Sum(Sales)
      mapSalesByState/visual.json      ← azureMap:   State (Location) × Sum(Sales)
```

The visuals bind to entity `Orders_ECFCA1FB690A41FE803BC071773BA862`, columns
`Category`, `State`, `Sales` — the real names our compiler emits in
`data/Model.json`.

## 3. Point it at a semantic model

`definition.pbir` references `../Superstore.SemanticModel` (byPath). This sample
does **not** ship a semantic model. To verify rendering you need a Superstore
model with that table/columns. Options:

- Easiest: open Power BI Desktop → connect to the Superstore data → save as
  `.pbip` (this creates a `*.SemanticModel` folder), then drop these two
  `visual.json` files into its `definition/pages/.../visuals/` and reload; **or**
- Point `definition.pbir` `byPath` at an existing Superstore `*.SemanticModel`
  folder; **or**
- Use `byConnection` to a published Superstore model.

## 4. Open and verify

1. Double-click `Superstore.pbip` (or **File → Open** the `.pbip`).
2. If Desktop reports a **blocking error**, it names the offending file — open it
   in VS Code (the `$schema` line gives IntelliSense) and fix the flagged
   property. Likely spots: exact `version` strings, or a required field this
   draft omitted in `report.json`/`page.json`.
3. Confirm the column chart shows **Sales by Category** and the Azure Map shows
   **Sales by State** (bubbles sized by Sales).
4. Record the result back in `../FEASIBILITY.md` (renders / needed-fixes).

## 5. If you want a true filled choropleth

Create a filled map manually in Power BI (legacy `filledMap`, deprecated, or an
`azureMap` with a choropleth/reference layer), save as `.pbip`, and share the
resulting `visual.json` — the assistant will reverse-document it. See
`ANNOTATIONS.md` §3.
