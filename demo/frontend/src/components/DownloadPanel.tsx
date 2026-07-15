import { downloadUrl } from "../api";
import type { CombinedReport } from "../types";

export default function DownloadPanel({ report, onReset }: { report: CombinedReport; onReset: () => void }) {
  const param = report.packaging.data_folder_param;
  const steps = [
    <>Unzip the download. It contains the <code>.pbip</code>, the model, the report, and a <code>data/</code> folder of CSVs.</>,
    <>Open the <code>.pbip</code> in <strong>Power BI Desktop</strong> (enable the PBIP + PBIR preview features first).</>,
    <>Set the <code>{param}</code> parameter to the extracted <code>data</code> folder path, then click <strong>Refresh</strong> to load the data.</>,
    <>The model, relationships, measures, and visuals load — confirm it renders (that’s the real check).</>,
  ];

  return (
    <div className="anim-scale-in rounded-2xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-6 shadow-lg shadow-slate-200/50 dark:border-slate-700 dark:from-slate-800/70 dark:to-slate-900/40 dark:shadow-black/20">
      <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Your Power BI project is ready</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Portable <code>.pbip</code> with data bundled as CSVs — {report.packaging.bundled_csvs.length} table(s).
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={downloadUrl(report.download.token)}
            download={report.download.filename}
            className="shine rounded-xl bg-brand px-5 py-2.5 font-semibold text-brand-ink shadow-lg shadow-amber-300/40 transition hover:-translate-y-0.5 hover:shadow-xl hover:shadow-amber-300/50 focus:outline-none focus:ring-2 focus:ring-brand active:translate-y-0"
          >
            ⬇ Download .pbip
          </a>
          <button
            onClick={onReset}
            className="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Convert another
          </button>
        </div>
      </div>

      <div className="mt-6">
        <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
          How to open
        </h4>
        <ol className="space-y-2">
          {steps.map((s, i) => (
            <li
              key={i}
              className="anim-fade-up flex gap-3 text-sm text-slate-700 dark:text-slate-300"
              style={{ animationDelay: `${200 + i * 90}ms` }}
            >
              <span className="grid h-5 w-5 flex-none place-items-center rounded-full bg-brand/20 text-xs font-bold text-amber-800 dark:text-amber-300">
                {i + 1}
              </span>
              <span>{s}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-500 dark:bg-slate-900/50 dark:text-slate-400">
          <strong>Portability note:</strong> data is bundled as CSVs and the path is a parameter, so the
          project works on any machine after you point <code>{param}</code> at the extracted <code>data</code>
          folder. (The compiler itself writes an absolute path; this download is repackaged to be portable.)
        </p>
      </div>
    </div>
  );
}
