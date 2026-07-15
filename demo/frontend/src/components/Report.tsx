import type { CombinedReport } from "../types";
import { Bar, Card, Chip, Note, Stat } from "./ui";

export default function Report({ report }: { report: CombinedReport }) {
  const m = report.model;
  const cr = m.conversion_report;
  const v = report.visuals;

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      {/* Model */}
      <Card title="Semantic model (TMDL)" icon={<span>🧮</span>} delay={80}>
        <div className="grid grid-cols-4 gap-2">
          <Stat label="measures" value={m.tmdl.measures} />
          <Stat label="calc cols" value={m.tmdl.calculated_columns} />
          <Stat label="parameters" value={m.tmdl.parameters} />
          <Stat label="relationships" value={m.tmdl.relationships} />
        </div>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Measure coverage (measures + columns / total calcs)</span>
            <span className="font-semibold">{cr.coverage_pct}%</span>
          </div>
          <Bar pct={cr.coverage_pct} />
        </div>
        {m.tmdl_skipped_multiline.length > 0 && (
          <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            {m.tmdl_skipped_multiline.length} multi-line calc not emitted as TMDL (would break model load) — reported, not faked.
          </p>
        )}
        <SkipList title="Skipped calculations" buckets={cr.failure_taxonomy} />
      </Card>

      {/* Visuals */}
      <Card title="Report visuals (PBIR)" icon={<span>📊</span>} delay={200}>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="worksheets" value={v.worksheets_total} />
          <Stat label="emitted" value={v.visuals_emitted} />
          <Stat label="skipped" value={v.visuals_skipped} />
        </div>
        <div className="mt-4">
          <div className="mb-1 flex justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>Visual coverage (emitted & schema-valid / worksheets)</span>
            <span className="font-semibold">{v.coverage_pct_schema_valid}%</span>
          </div>
          <Bar pct={v.coverage_pct_schema_valid} />
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {Object.entries(v.emitted_by_type).map(([t, n]) => (
            <Chip key={t} tone="green">
              {t} · {n}
            </Chip>
          ))}
        </div>
        <SkipList title="Skipped worksheets" buckets={v.skipped_by_bucket} />
      </Card>

      {/* Honest labels — full width */}
      <div className="space-y-3 lg:col-span-2">
        <Note>
          <strong>Not render-verified.</strong> Coverage counts what compiled and is schema-valid — it
          does <em>not</em> mean the report renders yet. Open the downloaded <code>.pbip</code> in Power BI
          Desktop to confirm. {report.render_verified.replace(/^pending\s*/i, "")}
        </Note>
        <Note>
          <strong>Maps use Bing/Azure geocoding</strong>, not Tableau’s proprietary geocoder — results are
          semantically right but not point-identical. Custom-geometry / filled-region maps are reported as
          unsupported, never faked.
        </Note>
      </div>
    </div>
  );
}

function SkipList({ title, buckets }: { title: string; buckets: Record<string, number> }) {
  const entries = Object.entries(buckets).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return (
    <details className="mt-4 text-sm">
      <summary className="cursor-pointer select-none text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200">
        {title} — {entries.reduce((s, [, n]) => s + n, 0)} (with reasons)
      </summary>
      <ul className="mt-2 space-y-1">
        {entries.map(([bucket, n]) => (
          <li key={bucket} className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-1.5 dark:bg-slate-900/40">
            <code className="text-xs text-slate-600 dark:text-slate-300">{bucket}</code>
            <span className="text-xs font-semibold tabular-nums text-slate-500">{n}</span>
          </li>
        ))}
      </ul>
    </details>
  );
}
