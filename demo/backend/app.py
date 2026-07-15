"""FastAPI backend for the tab2pbi demo.

Upload a .twbx, run the compiler in an isolated temp dir, get the conversion
report back as JSON, and download a portable .pbip zip. The compiler itself is
untouched; portability is handled by ``packaging.make_portable_zip``.
"""

from __future__ import annotations

import re
import secrets
import shutil
import sys
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

# Make the compiler importable from a source checkout (no install required).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tab2pbi import build_pbip  # noqa: E402

from . import packaging  # noqa: E402
from .validation import DemoError, validate_twbx  # noqa: E402

MAX_UPLOAD_BYTES = 50 * 1024 * 1024      # 50 MB
TOKEN_TTL_SECONDS = 30 * 60              # 30 min
WORKROOT = Path(__file__).resolve().parent / ".work"

app = FastAPI(title="tab2pbi demo", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# token -> {"zip": Path, "workdir": Path, "filename": str, "expires": float}
_downloads: dict[str, dict] = {}


def _sanitize_name(filename: str | None) -> str:
    stem = Path(filename or "Workbook").stem
    clean = re.sub(r"[^A-Za-z0-9_-]", "_", stem).strip("_")
    return clean or "Workbook"


def _purge_expired() -> None:
    now = time.time()
    for token in [t for t, e in _downloads.items() if e["expires"] < now]:
        entry = _downloads.pop(token)
        shutil.rmtree(entry["workdir"], ignore_errors=True)


@app.post("/api/convert")
async def convert(file: UploadFile = File(...)):  # noqa: B008  (FastAPI dependency pattern)
    _purge_expired()
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        return JSONResponse(status_code=413, content={
            "error": f"File too large ({len(data) // (1024 * 1024)} MB). Limit is "
                     f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."})

    try:
        validate_twbx(data)
    except DemoError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})

    name = _sanitize_name(file.filename)
    WORKROOT.mkdir(parents=True, exist_ok=True)
    workdir = Path(WORKROOT) / secrets.token_hex(8)
    (workdir / "in").mkdir(parents=True)
    twbx_path = workdir / "in" / f"{name}.twbx"
    twbx_path.write_bytes(data)

    try:
        combined = build_pbip.run(
            twbx_path=twbx_path,
            out_dir=workdir / "pbip",
            name=name,
            data_dir=workdir / "data",
        )
        pkg = packaging.make_portable_zip(
            pbip_dir=workdir / "pbip",
            name=name,
            csv_dir=workdir / "data" / "tables",
            dest_zip=workdir / f"{name}.zip",
        )
    except Exception:  # never leak a stack trace to the client
        shutil.rmtree(workdir, ignore_errors=True)
        return JSONResponse(status_code=500, content={
            "error": "Conversion failed. The workbook may use an unsupported "
                     "structure. Try the bundled Superstore sample to confirm setup."})

    token = secrets.token_urlsafe(16)
    _downloads[token] = {
        "zip": workdir / f"{name}.zip",
        "workdir": workdir,
        "filename": f"{name}.zip",
        "expires": time.time() + TOKEN_TTL_SECONDS,
    }

    combined["download"] = {"token": token, "filename": f"{name}.zip"}
    combined["packaging"] = {
        "portable": True,
        "bundled_csvs": pkg["csvs"],
        "data_folder_param": packaging.PARAM_NAME,
        "note": ("Data is bundled as CSVs. After extracting, open the .pbip, set the "
                 f"'{packaging.PARAM_NAME}' parameter to the extracted 'data' folder, then Refresh."),
    }
    return combined


@app.get("/api/download/{token}")
def download(token: str):
    _purge_expired()
    entry = _downloads.get(token)
    if not entry or not Path(entry["zip"]).exists():
        return JSONResponse(status_code=404, content={
            "error": "This download has expired. Please convert the workbook again."})
    return FileResponse(entry["zip"], media_type="application/zip", filename=entry["filename"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
