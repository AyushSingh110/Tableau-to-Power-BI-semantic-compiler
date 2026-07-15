# tab2pbi demo — web app

A self-service web app: **upload a Tableau `.twbx`, see an honest conversion
report in the browser, and download a portable Power BI `.pbip`** to open in
Power BI Desktop.

- **Backend** — `demo/backend/` (FastAPI): validates the upload, runs
  `tab2pbi.build_pbip` in an isolated temp dir, and returns the conversion report
  + a short-lived download token. Portability is handled by a demo-side packager
  (`packaging.py`) — **the compiler itself is untouched.**
- **Frontend** — `demo/frontend/` (React + Vite + Tailwind): drag-and-drop
  upload, a clean report view (model + visual coverage, skip taxonomy with
  reasons, honest labels), and a Download + "How to open" panel. Light/dark,
  responsive, no runtime CDN calls.

## Run it

Two terminals from the repo root.

**1. Backend** (needs the compiler installed):

```bash
pip install -e .                              # the tab2pbi compiler + deps
pip install -r demo/backend/requirements.txt  # FastAPI, uvicorn
uvicorn demo.backend.app:app --reload --port 8000
```

**2. Frontend:**

```bash
cd demo/frontend
npm install
npm run dev            # http://localhost:5173  (proxies /api → :8000)
```

Open <http://localhost:5173>, drop in `examples/Superstore.twbx`, read the
report, and click **Download .pbip**.

## What it does (and the honest limits)

- The report is **schema-valid coverage, NOT render-verified** — it means the
  model + visuals compiled and validate, not that they render. Only opening the
  `.pbip` in **Power BI Desktop** confirms that.
- **You need Power BI Desktop** (with the PBIP + PBIR preview features enabled)
  to open the output. The app produces the project; it doesn't render it.
- **Portability:** the compiler writes an *absolute* CSV path in the model. The
  download is **repackaged to be portable** — the per-table CSVs are bundled and
  the path is a Power BI `DataFolder` **parameter**. After extracting, open the
  `.pbip`, set `DataFolder` to the extracted `data` folder, and **Refresh**. If
  it's left unset the model raises a clear error on refresh — it never silently
  loads empty.
- **Maps** use Bing/Azure geocoding, not Tableau's proprietary geocoder —
  semantically right, not point-identical. Custom-geometry maps are reported as
  unsupported.

## Tests

```bash
# backend (from repo root)
pip install -r demo/backend/requirements.txt
pytest demo/backend/tests

# frontend (typecheck + production build)
cd demo/frontend && npm run build
```

## CLI alternative

Prefer the command line? The same end-to-end compile is one command:

```bash
tab2pbi build-pbip examples/Superstore.twbx     # writes data/pbip/Superstore.pbip
```

See [`../docs/VISUAL.md`](../docs/VISUAL.md) for the render-gate checklist.
