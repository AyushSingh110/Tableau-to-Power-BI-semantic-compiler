import { useEffect, useState } from "react";

const STAGES = [
  "Unpacking the .twbx",
  "Parsing workbook + Hyper extract",
  "Building the semantic model & DAX",
  "Inferring relationships",
  "Translating worksheets → visuals",
  "Packaging a portable .pbip",
];

export default function Converting({ filename }: { filename: string }) {
  const [active, setActive] = useState(0);
  useEffect(() => {
    // Advance the visible stage on a timer to convey progress; the real work is
    // one request, so the last stage holds until it resolves.
    const id = setInterval(() => setActive((a) => Math.min(a + 1, STAGES.length - 1)), 550);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="mx-auto max-w-md py-12 text-center anim-fade-in">
      <div className="relative mx-auto mb-8 h-20 w-20">
        <div className="absolute inset-0 rounded-full border-4 border-slate-200 dark:border-slate-700" />
        <div
          className="absolute inset-0 rounded-full border-4 border-transparent border-t-brand"
          style={{ animation: "ring 0.9s linear infinite" }}
        />
        <div className="absolute inset-0 grid place-items-center text-2xl anim-float">⚙️</div>
      </div>

      <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">
        Compiling <span className="text-brand">{filename}</span>…
      </p>

      <ul className="mx-auto mt-6 max-w-sm space-y-2 text-left">
        {STAGES.map((label, i) => {
          const done = i < active;
          const current = i === active;
          return (
            <li
              key={label}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-300 ${
                current
                  ? "bg-amber-50 text-slate-900 dark:bg-amber-400/10 dark:text-white"
                  : done
                    ? "text-slate-500 dark:text-slate-400"
                    : "text-slate-300 dark:text-slate-600"
              }`}
            >
              <span
                className={`grid h-5 w-5 flex-none place-items-center rounded-full text-[11px] transition ${
                  done
                    ? "bg-emerald-500 text-white"
                    : current
                      ? "bg-brand text-brand-ink"
                      : "bg-slate-200 dark:bg-slate-700"
                }`}
              >
                {done ? "✓" : current ? <span className="h-2 w-2 animate-ping rounded-full bg-brand-ink/70" /> : ""}
              </span>
              {label}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
