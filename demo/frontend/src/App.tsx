import { useState } from "react";
import { convert } from "./api";
import Converting from "./components/Converting";
import DownloadPanel from "./components/DownloadPanel";
import Dropzone from "./components/Dropzone";
import Header from "./components/Header";
import Report from "./components/Report";
import type { CombinedReport } from "./types";

type Stage = "idle" | "converting" | "done";

function Aurora() {
  // Self-contained animated background (no external assets).
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="blob absolute -left-32 -top-32 h-96 w-96 rounded-full bg-amber-300/30 blur-3xl dark:bg-amber-500/10" />
      <div className="blob absolute right-[-10rem] top-24 h-[28rem] w-[28rem] rounded-full bg-sky-300/25 blur-3xl dark:bg-sky-500/10" style={{ animationDelay: "-6s" }} />
      <div className="blob absolute bottom-[-12rem] left-1/3 h-[30rem] w-[30rem] rounded-full bg-violet-300/20 blur-3xl dark:bg-violet-500/10" style={{ animationDelay: "-12s" }} />
    </div>
  );
}

export default function App() {
  const [stage, setStage] = useState<Stage>("idle");
  const [report, setReport] = useState<CombinedReport | null>(null);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState<string>();

  async function handleFile(file: File) {
    setError(undefined);
    setFilename(file.name);
    setStage("converting");
    try {
      setReport(await convert(file));
      setStage("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Conversion failed.");
      setStage("idle");
    }
  }

  function reset() {
    setStage("idle");
    setReport(null);
    setError(undefined);
  }

  return (
    <div className="relative min-h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <Aurora />
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <Header />

        <main className="mt-10">
          {stage === "idle" && (
            <div key="idle">
              <div className="mb-10 text-center">
                <span className="anim-fade-up inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs font-medium text-slate-500 backdrop-blur dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-400">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
                  Deterministic · no silent drops · open-source
                </span>
                <h2 className="anim-fade-up mt-4 text-3xl font-bold tracking-tight sm:text-5xl" style={{ animationDelay: "60ms" }}>
                  Turn a Tableau workbook into a{" "}
                  <span className="bg-gradient-to-r from-amber-500 to-brand bg-clip-text text-transparent">
                    Power BI project
                  </span>
                </h2>
                <p className="anim-fade-up mx-auto mt-4 max-w-2xl text-slate-500 dark:text-slate-400" style={{ animationDelay: "140ms" }}>
                  Upload a <code>.twbx</code>, get an honest conversion report, and download a
                  <code> .pbip</code> that opens in Power BI Desktop — model, measures, relationships,
                  and visuals. Anything that can’t be translated is reported with a reason, never faked.
                </p>
              </div>
              <div className="anim-fade-up" style={{ animationDelay: "220ms" }}>
                <Dropzone onFile={handleFile} error={error} />
              </div>
            </div>
          )}

          {stage === "converting" && <Converting filename={filename} />}

          {stage === "done" && report && (
            <div key="done" className="space-y-6">
              <DownloadPanel report={report} onReset={reset} />
              <Report report={report} />
            </div>
          )}
        </main>

        <footer className="anim-fade-in mt-16 border-t border-slate-200 pt-6 text-center text-xs text-slate-400 dark:border-slate-800">
          <p>
            <strong>tab2pbi</strong> — a deterministic, no-silent-drop compiler. Needs Power BI Desktop to
            open the output. Coverage is schema-valid, not render-verified until you open it.
          </p>
        </footer>
      </div>
    </div>
  );
}
