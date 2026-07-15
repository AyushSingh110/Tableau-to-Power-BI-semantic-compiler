export default function Converting({ filename }: { filename: string }) {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <div className="mx-auto mb-6 h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-brand dark:border-slate-700 dark:border-t-brand" />
      <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">Compiling {filename}…</p>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
        Parsing the workbook, building the semantic model &amp; DAX, inferring relationships,
        translating visuals, and packaging a portable <code>.pbip</code>.
      </p>
    </div>
  );
}
