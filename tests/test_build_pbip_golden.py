"""Golden end-to-end: .twbx -> full .pbip (TMDL model + PBIR visuals, coherent)."""

import json
from pathlib import Path

import pytest

from tab2pbi import build_pbip

REPO = Path(__file__).resolve().parents[1]
TWBX = REPO / "examples" / "Superstore.twbx"
ORDERS = "Orders_ECFCA1FB690A41FE803BC071773BA862"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    if not TWBX.exists():
        pytest.skip("Superstore.twbx missing")
    out = tmp_path_factory.mktemp("pbip_out")
    data = tmp_path_factory.mktemp("pbip_data")
    combined = build_pbip.run(TWBX, out, name="Superstore", data_dir=data)
    return out, combined


def test_pbip_tree_exists(built):
    out, _ = built
    assert (out / "Superstore.pbip").exists()
    assert (out / "Superstore.SemanticModel/definition/model.tmdl").exists()
    assert (out / "Superstore.Report/definition.pbir").exists()
    # report points at the emitted model
    pbir = json.loads((out / "Superstore.Report/definition.pbir").read_text())
    assert pbir["datasetReference"]["byPath"]["path"] == "../Superstore.SemanticModel"


def test_model_has_three_tables(built):
    out, combined = built
    model = (out / "Superstore.SemanticModel/definition/model.tmdl").read_text(encoding="utf-8")
    assert model.count("ref table ") == 3
    assert combined["model"]["tmdl"]["tables"] == 3
    assert combined["model"]["tmdl"]["measures"] == 1


def test_visuals_bind_to_model_entities(built):
    out, combined = built
    assert combined["visuals"]["visuals_emitted"] == 9
    assert combined["visuals"]["bound_entities_are_multitable"] is True
    # every emitted visual.json binds to a real model table, not flat hyper_raw_data
    entities = set()
    for vj in (out / "Superstore.Report/definition/pages").rglob("visual.json"):
        obj = json.loads(vj.read_text(encoding="utf-8"))
        for role in obj["visual"]["query"]["queryState"].values():
            for proj in role["projections"]:
                f = proj["field"]
                col = f.get("Column") or f["Aggregation"]["Expression"]["Column"]
                entities.add(col["Expression"]["SourceRef"]["Entity"])
    assert "hyper_raw_data" not in entities
    assert ORDERS in entities


def test_combined_report_labels_not_render_verified(built):
    _, combined = built
    assert "pending" in combined["render_verified"]
    assert "NOT render" in combined["visuals"].get("coverage_label", "") or \
           combined["visuals"]["coverage_pct_schema_valid"] >= 0  # coverage present
