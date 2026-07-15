// Small shared UI primitives — kept in one place so cards/stats/chips are
// consistent and not re-styled per component.
import type { ReactNode } from "react";

export function Card({ title, icon, children }: { title: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800/60">
      <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3 text-center dark:bg-slate-900/50">
      <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-white">{value}</div>
      <div className="mt-0.5 text-xs font-medium text-slate-500 dark:text-slate-400">{label}</div>
      {hint && <div className="mt-0.5 text-[10px] text-slate-400">{hint}</div>}
    </div>
  );
}

const CHIP_TONE: Record<string, string> = {
  brand: "bg-amber-100 text-amber-900 dark:bg-amber-400/15 dark:text-amber-300",
  green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-400/15 dark:text-emerald-300",
  slate: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300",
  amber: "bg-orange-100 text-orange-800 dark:bg-orange-400/15 dark:text-orange-300",
};

export function Chip({ children, tone = "slate" }: { children: ReactNode; tone?: keyof typeof CHIP_TONE }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${CHIP_TONE[tone]}`}>
      {children}
    </span>
  );
}

export function Bar({ pct }: { pct: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
      <div className="h-full rounded-full bg-brand" style={{ width: `${Math.max(2, Math.min(100, pct))}%` }} />
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
      {children}
    </p>
  );
}
