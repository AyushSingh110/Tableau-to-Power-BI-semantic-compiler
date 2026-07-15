"""Integration tests for the convert -> download flow."""

import io
import zipfile
import zipfile as _zip
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from demo.backend import app as app_module
from demo.backend.app import app

REPO = Path(__file__).resolve().parents[3]
TWBX = REPO / "examples" / "Superstore.twbx"

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_reject_non_zip():
    r = client.post("/api/convert", files={"file": ("x.twbx", b"nope", "application/octet-stream")})
    assert r.status_code == 400 and "error" in r.json()


def test_reject_missing_hyper():
    buf = io.BytesIO()
    with _zip.ZipFile(buf, "w") as z:
        z.writestr("wb.twb", b"<workbook/>")
    r = client.post("/api/convert", files={"file": ("x.twbx", buf.getvalue(), "application/octet-stream")})
    assert r.status_code == 400 and "hyper" in r.json()["error"].lower()


def test_oversize_rejected(monkeypatch):
    monkeypatch.setattr(app_module, "MAX_UPLOAD_BYTES", 4)
    r = client.post("/api/convert", files={"file": ("x.twbx", b"12345", "application/octet-stream")})
    assert r.status_code == 413


def test_download_bad_token():
    assert client.get("/api/download/nope").status_code == 404


@pytest.mark.skipif(not TWBX.exists(), reason="Superstore.twbx missing")
def test_convert_download_happy_path():
    r = client.post("/api/convert",
                    files={"file": ("Superstore.twbx", TWBX.read_bytes(), "application/octet-stream")})
    assert r.status_code == 200
    j = r.json()
    # report shape
    assert j["model"]["tmdl"]["tables"] == 3
    assert j["visuals"]["visuals_emitted"] == 9
    assert j["packaging"]["portable"] is True and j["packaging"]["bundled_csvs"]
    token = j["download"]["token"]

    d = client.get(f"/api/download/{token}")
    assert d.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(d.content))
    names = z.namelist()
    assert any(n.endswith(".pbip") for n in names)
    assert any(n.startswith("data/") and n.endswith(".csv") for n in names)
    assert any(n.endswith("expressions.tmdl") for n in names)
    tbl = next(n for n in names if n.endswith(".tmdl") and "/tables/" in n)
    assert "DataFolder &" in z.read(tbl).decode()
