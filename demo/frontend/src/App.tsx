import { useState } from "react";
import { convert } from "./api";
import Converting from "./components/Converting";
import DownloadPanel from "./components/DownloadPanel";
import Dropzone from "./components/Dropzone";
import Header from "./components/Header";
import Report from "./components/Report";
import type { CombinedReport } from "./types";

type Stage = "idle" | "converting" | "done";

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
    <div className="min-h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6">
        <Header />

        <main className="mt-10">
          {stage === "idle" && (
            <>
              <div className="mb-10 text-center">
                <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                  Turn a Tableau workbook into a Power BI project
                </h2>
                <p className="mx-auto mt-3 max-w-2xl text-slate-500 dark:text-slate-400">
                  Upload a <code>.twbx</code>, get an honest conversion report, and download a
                  <code> .pbip</code> that opens in Power BI Desktop — model, measures, relationships,
                  and visuals. Anything that can’t be translated is reported with a reason, never faked.
                </p>
              </div>
              <Dropzone onFile={handleFile} error={error} />
            </>
          )}

          {stage === "converting" && <Converting filename={filename} />}

          {stage === "done" && report && (
            <div className="space-y-6">
              <DownloadPanel report={report} onReset={reset} />
              <Report report={report} />
            </div>
          )}
        </main>

        <footer className="mt-16 border-t border-slate-200 pt-6 text-center text-xs text-slate-400 dark:border-slate-800">
          <p>
            <strong>tab2pbi</strong> — a deterministic, no-silent-drop compiler. Needs Power BI Desktop to
            open the output. Coverage is schema-valid, not render-verified until you open it.
          </p>
        </footer>
      </div>
    </div>
  );
}
