import { useRef, useState } from "react";

export default function Dropzone({ onFile, error }: { onFile: (f: File) => void; error?: string }) {
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  function pick(files: FileList | null) {
    if (files && files.length) onFile(files[0]);
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div
        role="button"
        tabIndex={0}
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          pick(e.dataTransfer.files);
        }}
        className={`cursor-pointer rounded-3xl border-2 border-dashed p-12 text-center transition
          ${drag
            ? "border-brand bg-amber-50 dark:bg-amber-400/10"
            : "border-slate-300 bg-white hover:border-brand hover:bg-slate-50 dark:border-slate-600 dark:bg-slate-800/50 dark:hover:bg-slate-800"}`}
      >
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-brand/15 text-3xl">📊</div>
        <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          Drop a Tableau <code className="rounded bg-slate-100 px-1 dark:bg-slate-700">.twbx</code> here
        </p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">or click to browse — max 50&nbsp;MB, must embed a Hyper extract</p>
        <input
          ref={input}
          type="file"
          accept=".twbx"
          className="hidden"
          onChange={(e) => pick(e.target.files)}
        />
      </div>

      {error && (
        <p className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300">
          {error}
        </p>
      )}

      <p className="mt-6 text-center text-xs text-slate-400">
        No workbook? Use the bundled <span className="font-medium">Superstore</span> sample from the repo
        (<code>examples/Superstore.twbx</code>).
      </p>
    </div>
  );
}
