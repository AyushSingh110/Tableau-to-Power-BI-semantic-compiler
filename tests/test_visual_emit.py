"""Emitter tests: emitted visual.json matches the reference skeleton + validates."""

import json
from pathlib import Path

import pytest

from tab2pbi.visual import emit_pbir
from tab2pbi.visual.emit_pbir import StructuralError, structural_check
from tab2pbi.visual.ir import FieldRef, PageNode, Position, VisualNode

REPO = Path(__file__).resolve().parents[1]
REF_PAGES = REPO / "experiments/visual-spike/pbir_reference/Superstore.Report/definition/pages"


def _reference_visual(visual_type: str) -> dict | None:
    """Find any committed reference visual.json of the given type (GUID-agnostic).

    Power BI re-saves the reference with fresh GUIDs, so we discover by content
    rather than hard-coding a path.
    """
    if not REF_PAGES.exists():
        return None
    for vj in REF_PAGES.rglob("visual.json"):
        obj = json.loads(vj.read_text(encoding="utf-8"))
        if obj.get("visual", {}).get("visualType") == visual_type:
            return obj
    return None


def _map_node():
    v = VisualNode(
        worksheet="Sales by State - Map", mark_type="Multipolygon", visual_type="map",
        wells={
            "Category": [FieldRef("hyper_raw_data", "State", None)],
            "Size": [FieldRef("hyper_raw_data", "Sales", "sum")],
        },
        position=Position(10, 10, 0, 300, 300),
    )
    return PageNode(id="", name="P1", display_name="P1", visuals=[v])


def test_emit_produces_valid_tree(tmp_path):
    info = emit_pbir.emit([_map_node()], tmp_path / "R.Report", "../Superstore.SemanticModel")
    assert info["emitted_visuals"] == 1 and info["pages"] == 1
    # scaffolding present
    defn = tmp_path / "R.Report" / "definition"
    for f in ("report.json", "version.json", "pages/pages.json"):
        assert (defn / f).exists()
    assert (tmp_path / "R.Report" / "definition.pbir").exists()
    # the emitted visual.json validates structurally
    vj = next((defn / "pages").rglob("visual.json"))
    structural_check(json.loads(vj.read_text(encoding="utf-8")))


def test_emitted_map_matches_reference_skeleton(tmp_path):
    ref = _reference_visual("map")
    if ref is None:
        pytest.skip("no committed reference map visual.json to diff against")
    emit_pbir.emit([_map_node()], tmp_path / "R.Report", "../m")
    emitted = json.loads(next((tmp_path / "R.Report" / "definition/pages").rglob("visual.json")).read_text())
    assert emitted["$schema"] == ref["$schema"]
    assert emitted["visual"]["visualType"] == ref["visual"]["visualType"] == "map"
    assert set(emitted["visual"]["query"]["queryState"]) == set(ref["visual"]["query"]["queryState"])
    # same projection field skeleton for the Category role
    e_field = emitted["visual"]["query"]["queryState"]["Category"]["projections"][0]["field"]
    r_field = ref["visual"]["query"]["queryState"]["Category"]["projections"][0]["field"]
    assert set(e_field) == set(r_field) == {"Column"}


def test_structural_check_rejects_bad():
    with pytest.raises(StructuralError):
        structural_check({"$schema": "wrong", "name": "x"})
    with pytest.raises(StructuralError):
        structural_check({"$schema": emit_pbir.VISUAL_SCHEMA, "name": "x",
                          "position": {"x": 0, "y": 0, "z": 0, "width": 1, "height": 1},
                          "visual": {"visualType": "columnChart", "query": {"queryState": {}}}})
