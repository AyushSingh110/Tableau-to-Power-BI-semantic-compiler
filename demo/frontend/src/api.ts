import type { CombinedReport } from "./types";

export async function convert(file: File): Promise<CombinedReport> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/convert", { method: "POST", body: form });
  const json = await res.json().catch(() => ({ error: "Unexpected server response." }));
  if (!res.ok) {
    throw new Error(json.error ?? `Conversion failed (HTTP ${res.status}).`);
  }
  return json as CombinedReport;
}

export function downloadUrl(token: string): string {
  return `/api/download/${token}`;
}
