"""Build the visual_conversion_report and a human summary.

Coverage is deliberately labeled as *emitted & schema-valid / total worksheets*
— NOT render-verified. This mirrors the model side's proxy-vs-engine-verified
distinction: a schema-valid report is necessary but not sufficient; only opening
it in Power BI Desktop confirms the visuals actually render.
"""

from __future__ import annotations

from collections import Counter

from .ir import SKIP_BUCKETS, PageNode


def build_report(pages: list[PageNode]) -> dict:
    # Dedupe by worksheet: a sheet placed on multiple dashboard pages is one
    # worksheet, not several, so coverage is over UNIQUE worksheets.
    unique: dict[str, object] = {}
    for p in pages:
        for v in p.visuals:
            unique.setdefault(v.worksheet, v)
    visuals = list(unique.values())
    total = len(visuals)
    emitted = [v for v in visuals if v.emitted]
    skipped = [v for v in visuals if not v.emitted]

    per_type = Counter(v.visual_type for v in emitted)
    per_bucket = {b: 0 for b in SKIP_BUCKETS}
    for v in skipped:
        per_bucket[v.skip_reason] = per_bucket.get(v.skip_reason, 0) + 1

    return {
        "worksheets_total": total,
        "visuals_emitted": len(emitted),
        "visuals_skipped": len(skipped),
        "emitted_by_type": dict(per_type),
        "skipped_by_bucket": {k: v for k, v in per_bucket.items() if v},
        "coverage_pct_schema_valid": round(100 * len(emitted) / total, 1) if total else 0.0,
        "coverage_label": "emitted & schema-valid / total worksheets (NOT render-verified)",
        "render_verified": "pending (open in Power BI Desktop — see render-gate)",
    }


def summary(report: dict, pages: list[PageNode]) -> str:
    lines = [
        "",
        "=" * 62,
        " tab2pbi VISUAL compiler summary",
        "=" * 62,
        f" Worksheets:          {report['worksheets_total']}",
        f" Visuals emitted:     {report['visuals_emitted']}",
        f" Visuals skipped:     {report['visuals_skipped']}",
        f" Coverage:            {report['coverage_pct_schema_valid']}%  "
        f"({report['coverage_label']})",
        f" Render-verified:     {report['render_verified']}",
    ]
    if report["emitted_by_type"]:
        lines.append(" Emitted by type:")
        for k, v in sorted(report["emitted_by_type"].items(), key=lambda kv: -kv[1]):
            lines.append(f"   {k:<16} {v}")
    if report["skipped_by_bucket"]:
        lines.append(" Skipped by bucket (with reason):")
        for k, v in sorted(report["skipped_by_bucket"].items(), key=lambda kv: -kv[1]):
            lines.append(f"   {k:<24} {v}")
    lines.append("=" * 62)
    return "\n".join(lines)
