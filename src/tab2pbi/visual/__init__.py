"""V1 visual compiler: Tableau worksheets -> Power BI PBIR report.

Additive and isolated from the shipped data-model pipeline. Emits only the
*Report* (PBIR visual.json + scaffolding); it does NOT emit a semantic model.

Honesty caveats carried throughout (see FEASIBILITY.md and HANDOFF_REPORT.md):
- The emitted visuals bind to a FLAT ``hyper_raw_data`` entity (the spike's
  saved model), which is NOT the multi-table TOM the data-model compiler emits.
  Unifying the two + a TMDL emitter is V2 — this is a known integration gap.
- "Schema-valid" is not "render-verified"; the coverage number says so.
"""

__all__ = ["ir", "mapping", "extract", "emit_pbir", "report"]
