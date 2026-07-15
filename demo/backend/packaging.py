"""Make a downloaded .pbip portable across machines.

The compiler emits TMDL import partitions with an ABSOLUTE
``Csv.Document(File.Contents("C:\\...\\table.csv"))`` path — correct on the
machine that generated it, useless on a downloader's machine. Rather than touch
the compiler, this demo-side packager post-processes the emitted
``*.SemanticModel`` so the download is portable:

1. bundle the per-table CSVs into the zip under ``data/``;
2. rewrite each partition to ``File.Contents(DataFolder & "\\table.csv")``;
3. add a Power BI ``DataFolder`` query parameter (a standard, documented feature)
   that the user points at the extracted ``data`` folder, then Refresh.

If ``DataFolder`` is left unset the model raises a clear error on Refresh — it
never silently loads empty.
"""

from __future__ import annotations

import re
import shutil
import uuid
import zipfile
from pathlib import Path

PARAM_NAME = "DataFolder"
_PLACEHOLDER = "PASTE-THE-PATH-TO-THE-EXTRACTED-data-FOLDER-HERE"
_FILECONTENTS_RE = re.compile(r'File\.Contents\("([^"]+)"\)')
_NS = uuid.UUID("2b7c1e00-0000-4000-8000-abcdef012345")


def _rewrite_partition_paths(sm_dir: Path) -> int:
    """Rewrite absolute File.Contents paths to DataFolder-relative. Returns count."""
    count = 0
    for tmdl in (sm_dir / "definition" / "tables").glob("*.tmdl"):
        text = tmdl.read_text(encoding="utf-8")

        def repl(m: re.Match) -> str:
            nonlocal count
            count += 1
            basename = Path(m.group(1).replace("\\", "/")).name
            return f'File.Contents({PARAM_NAME} & "\\{basename}")'

        new = _FILECONTENTS_RE.sub(repl, text)
        if new != text:
            tmdl.write_text(new, encoding="utf-8")
    return count


def _write_parameter(sm_dir: Path) -> None:
    """Emit expressions.tmdl with the DataFolder query parameter."""
    lineage = str(uuid.uuid5(_NS, "expression/DataFolder"))
    content = (
        f'expression {PARAM_NAME} = "{_PLACEHOLDER}" '
        'meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {lineage}\n"
    )
    (sm_dir / "definition" / "expressions.tmdl").write_text(content, encoding="utf-8")

    # Reference the parameter from model.tmdl (before the culture ref).
    model = sm_dir / "definition" / "model.tmdl"
    text = model.read_text(encoding="utf-8")
    if f"ref expression {PARAM_NAME}" not in text:
        if "ref cultureInfo" in text:
            text = text.replace("ref cultureInfo", f"ref expression {PARAM_NAME}\n\nref cultureInfo", 1)
        else:
            text += f"\nref expression {PARAM_NAME}\n"
        model.write_text(text, encoding="utf-8")


def make_portable_zip(pbip_dir: Path, name: str, csv_dir: Path, dest_zip: Path) -> dict:
    """Package a portable .pbip zip. Returns {files, csvs}."""
    pbip_dir, csv_dir, dest_zip = Path(pbip_dir), Path(csv_dir), Path(dest_zip)
    staging = dest_zip.parent / f"{name}_pkg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    # Copy the .pbip project (pointer + SemanticModel + Report).
    shutil.copy(pbip_dir / f"{name}.pbip", staging / f"{name}.pbip")
    shutil.copytree(pbip_dir / f"{name}.SemanticModel", staging / f"{name}.SemanticModel")
    shutil.copytree(pbip_dir / f"{name}.Report", staging / f"{name}.Report")

    # Bundle the per-table CSVs and make the model reference them portably.
    data_out = staging / "data"
    data_out.mkdir()
    csvs = sorted(csv_dir.glob("*.csv"))
    for csv in csvs:
        shutil.copy(csv, data_out / csv.name)

    sm_dir = staging / f"{name}.SemanticModel"
    rewritten = _rewrite_partition_paths(sm_dir)
    _write_parameter(sm_dir)

    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                arc = path.relative_to(staging).as_posix()
                z.write(path, arc)
                files.append(arc)

    shutil.rmtree(staging)
    return {"files": files, "csvs": [c.name for c in csvs], "partitions_rewritten": rewritten}
