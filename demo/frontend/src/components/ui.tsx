// Small shared UI primitives — kept in one place so cards/stats/chips are
// consistent and not re-styled per component. Includes light, purposeful
// animations (count-up, growing bars, staggered entrance).
import { useEffect, useRef, useState, type ReactNode } from "react";

/** Animate a number from 0 → value on mount (respects reduced-motion). */
export function CountUp({ value, duration = 900 }: { value: number; duration?: number }) {
  const [n, setN] = useState(0);
  const raf = useRef(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setN(value);
      return;
    }
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setN(value * eased);
      if (p < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [value, duration]);
  const isInt = Number.isInteger(value);
  return <>{isInt ? Math.round(n) : n.toFixed(1)}</>;
}

export function Card({
  title,
  icon,
  children,
  delay = 0,
}: {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  delay?: number;
}) {
  return (
    <section
      style={{ animationDelay: `${delay}ms` }}
      className="anim-fade-up rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-200/60 dark:border-slate-700 dark:bg-slate-800/60 dark:hover:shadow-black/30"
    >
      <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="group rounded-xl bg-slate-50 p-3 text-center transition-colors hover:bg-slate-100 dark:bg-slate-900/50 dark:hover:bg-slate-900">
      <div className="text-2xl font-bold tabular-nums text-slate-900 dark:text-white">
        <CountUp value={value} />
      </div>
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
    <span
      className={`anim-pop inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium transition-transform hover:scale-105 ${CHIP_TONE[tone]}`}
    >
      {children}
    </span>
  );
}

export function Bar({ pct }: { pct: number }) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const id = requestAnimationFrame(() => setW(Math.max(2, Math.min(100, pct))));
    return () => cancelAnimationFrame(id);
  }, [pct]);
  return (
    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700">
      <div
        className="bar-fill h-full rounded-full bg-gradient-to-r from-amber-400 to-brand"
        style={{ width: `${w}%` }}
      />
    </div>
  );
}

export function Note({ children }: { children: ReactNode }) {
  return (
    <p className="anim-fade-in rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-200">
      {children}
    </p>
  );
}
