# Demo screenshots (to be captured by the author)

These images are referenced by [`../README.md`](../README.md) but are **not yet
captured** — the assistant that built this demo cannot launch Tabular Editor.
Capture each once from `data/Model.json` opened in Tabular Editor 2/3 and save
with the exact filename below.

| Filename | Should show |
| -------- | ----------- |
| `01-model-tree.png` | The model tree expanded: the three tables (Orders/Returns/People), the generated measure on Orders, the `DATEDIFF` calculated column, and the parameter columns. |
| `02-measure-dax.png` | The `[Calculation_1368…]` measure selected, with its DAX `SUM(Orders_…[Profit]) / SUM(Orders_…[Sales])` visible in the expression editor. |
| `03-relationship.png` | The `Orders → People` relationship (Many-to-One on `Region`) in the diagram or Relationships list. |

Optional: a side-by-side of the same measure's value in Tableau vs Power BI —
this is the engine-verified check described in
[`../../docs/EVALUATION.md`](../../docs/EVALUATION.md).
