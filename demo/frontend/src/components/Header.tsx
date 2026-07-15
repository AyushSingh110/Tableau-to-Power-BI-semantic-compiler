import { useEffect, useState } from "react";

function useTheme() {
  const [dark, setDark] = useState(() => {
    const saved = localStorage.getItem("theme");
    if (saved) return saved === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);
  return { dark, toggle: () => setDark((d) => !d) };
}

export default function Header() {
  const { dark, toggle } = useTheme();
  return (
    <header className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl bg-brand font-bold text-brand-ink shadow">
          t2p
        </div>
        <div>
          <h1 className="text-lg font-bold leading-none text-slate-900 dark:text-white">tab2pbi</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">Tableau → Power BI, in your browser</p>
        </div>
      </div>
      <button
        onClick={toggle}
        aria-label="Toggle theme"
        className="rounded-lg border border-slate-200 p-2 text-slate-600 transition hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
      >
        {dark ? "☀️" : "🌙"}
      </button>
    </header>
  );
}
