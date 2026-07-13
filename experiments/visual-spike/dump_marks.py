from __future__ import annotations
import argparse
import json
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

# Marks-card / shelf encoding tags we care about 
ENCODING_TAGS = {
    "color", "size", "shape", "label", "text", "detail", "lod",
    "tooltip", "geometry", "path", "angle", "level",
}
# Field names Tableau treats as geographic used only as a heuristic flag .
GEO_NAMES = {
    "country", "country/region", "state", "state/province", "city",
    "region", "postal code", "zip code", "county", "latitude", "longitude",
}
_REF_RE = re.compile(r"^\[(?P<ds>[^\]]*)\]\.\[(?P<inner>[^\]]*)\]$")
_ROLE_FLAG_RE = re.compile(r"^[a-z]{2,3}$")


def parse_field_ref(ref: str) -> str | None:
    """Extract a clean field name from a Tableau field reference.
    """
    if not ref:
        return None
    m = _REF_RE.match(ref)
    inner = m.group("inner") if m else ref.strip("[]")
    parts = inner.split(":")
    if len(parts) >= 3 and _ROLE_FLAG_RE.match(parts[-1]):
        name = ":".join(parts[1:-1])          # strip leading agg + trailing flag
    else:
        name = inner
    return name.lstrip(":").strip() or None


def load_mapping(path: Path) -> dict[str, dict]:
    """logical field name (lower) -> {table, column} from the shipped artifact."""
    if not path.exists():
        return {}
    out = {}
    for m in json.loads(path.read_text(encoding="utf-8")):
        out[m["logical_field"].lower()] = {"table": m["table"], "column": m["physical_column"]}
    return out


def resolve(name: str | None, mapping: dict) -> dict:
    if not name:
        return {"field": None, "resolved": None}
    if name.lower().startswith("calculation_") or name in ("Measure Names", "Multiple Values"):
        return {"field": name, "resolved": "calculated/derived (not a physical column)"}
    hit = mapping.get(name.lower())
    return {"field": name, "resolved": hit}


def extract_twb(twbx: Path) -> ET.Element:
    tmp = Path(tempfile.mkdtemp(prefix="marks_"))
    with zipfile.ZipFile(twbx) as z:
        z.extractall(tmp)
    twb = next(tmp.rglob("*.twb"))
    return ET.parse(twb).getroot()


def summarize_worksheet(ws: ET.Element, mapping: dict) -> dict:
    name = ws.attrib.get("name", "?")
    marks = [m.attrib.get("class") for m in ws.findall(".//pane/mark")]
    rows = ws.find(".//table/rows")
    cols = ws.find(".//table/cols")

    encodings = []
    for enc in ws.findall(".//pane/encodings/*"):
        if enc.tag not in ENCODING_TAGS:
            continue
        field = parse_field_ref(enc.attrib.get("column", ""))
        encodings.append({"shelf": enc.tag, **resolve(field, mapping)})

    # Geographic flag: filled/polygon mark, a geometry encoding, or a geo field.
    is_geo = (
        "Multipolygon" in marks
        or any(e["shelf"] == "geometry" for e in encodings)
        or any((e["field"] or "").lower() in GEO_NAMES for e in encodings)
    )

    return {
        "worksheet": name,
        "mark_types": sorted(set(m for m in marks if m)),
        "rows_shelf": rows.text if rows is not None else None,
        "cols_shelf": cols.text if cols is not None else None,
        "encodings": encodings,
        "is_geographic": is_geo,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Dump Tableau worksheet marks (read-only spike).")
    ap.add_argument("--twbx", type=Path, default=Path("examples/Superstore.twbx"))
    ap.add_argument("--mapping", type=Path, default=Path("data/logical_physical_mapping.json"))
    ap.add_argument("--out", type=Path, default=Path("experiments/visual-spike/marks_dump.json"))
    args = ap.parse_args(argv)

    mapping = load_mapping(args.mapping)
    root = extract_twb(args.twbx)
    worksheets = [summarize_worksheet(ws, mapping) for ws in root.findall(".//worksheet")]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(worksheets, indent=2), encoding="utf-8")

    # ---- report ----
    mark_hist = Counter(m for ws in worksheets for m in ws["mark_types"])
    geo = [ws["worksheet"] for ws in worksheets if ws["is_geographic"]]
    print(f"worksheets: {len(worksheets)}")
    print(f"mapping entries loaded: {len(mapping)}" + ("" if mapping else "  (mapping file missing — run pipeline first)"))
    print("mark-type histogram (worksheets containing each mark):")
    for mk, n in mark_hist.most_common():
        print(f"  {mk:<14} {n}")
    print(f"geographic worksheets: {len(geo)}")
    for g in geo:
        print(f"  - {g}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
