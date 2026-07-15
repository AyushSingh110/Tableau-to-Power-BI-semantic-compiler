"""Unit tests for .twbx validation and the portability packager."""

import io
import zipfile
from pathlib import Path

import pytest

from demo.backend import packaging
from demo.backend.validation import DemoError, validate_twbx


def _zip(names: list[str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in names:
            z.writestr(n, b"x")
    return buf.getvalue()


def test_valid_twbx_passes():
    validate_twbx(_zip(["wb.twb", "Data/extract.hyper"]))


def test_not_a_zip_rejected():
    with pytest.raises(DemoError):
        validate_twbx(b"not a zip")


def test_missing_twb_rejected():
    with pytest.raises(DemoError):
        validate_twbx(_zip(["Data/extract.hyper"]))


def test_missing_hyper_rejected():
    with pytest.raises(DemoError, match="hyper"):
        validate_twbx(_zip(["wb.twb"]))


def test_packager_bundles_csvs_and_parameterizes(tmp_path):
    # Minimal emitted .pbip layout with an absolute-path partition.
    name = "M"
    pbip = tmp_path / "pbip"
    sm = pbip / f"{name}.SemanticModel" / "definition"
    (sm / "tables").mkdir(parents=True)
    (pbip / f"{name}.Report").mkdir(parents=True)
    (pbip / f"{name}.pbip").write_text("{}")
    (sm / "model.tmdl").write_text("model Model\n\nref table T\n\nref cultureInfo en-US\n")
    abs_csv = tmp_path / "data" / "tables" / "T.csv"
    abs_csv.parent.mkdir(parents=True)
    abs_csv.write_text("a,b\n1,2\n")
    (sm / "tables" / "T.tmdl").write_text(
        f'table T\n\tpartition T = m\n\t\tsource =\n\t\t\tlet\n'
        f'\t\t\t    Source = Csv.Document(File.Contents("{abs_csv}"),[Columns=2])\n\t\t\tin Source\n'
    )

    info = packaging.make_portable_zip(pbip, name, abs_csv.parent, tmp_path / "out.zip")
    assert info["partitions_rewritten"] == 1
    assert "T.csv" in info["csvs"]

    z = zipfile.ZipFile(tmp_path / "out.zip")
    names = z.namelist()
    assert f"{name}.pbip" in names
    assert "data/T.csv" in names
    assert f"{name}.SemanticModel/definition/expressions.tmdl" in names
    tbl = z.read(f"{name}.SemanticModel/definition/tables/T.tmdl").decode()
    assert 'File.Contents(DataFolder & "\\T.csv")' in tbl
    assert str(Path(abs_csv)) not in tbl                       # absolute path gone
    model = z.read(f"{name}.SemanticModel/definition/model.tmdl").decode()
    assert "ref expression DataFolder" in model
