"""Golden test: Superstore worksheets -> expected emitted/skipped counts."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from tab2pbi.visual import extract, report

REPO = Path(__file__).resolve().parents[1]
TWBX = REPO / "examples" / "Superstore.twbx"

COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer Name", "Segment",
    "Country/Region", "City", "State", "Postal Code", "Region", "Category",
    "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit",
]

# Snapshot — update deliberately when mapping/extraction changes.
EXPECTED_WORKSHEETS = 32
EXPECTED_EMITTED = 11
EXPECTED_BY_TYPE = {"columnChart": 5, "map": 1, "areaChart": 1, "pieChart": 1, "lineChart": 1, "tableEx": 2}
EXPECTED_SKIP = {"custom_shape": 11, "insufficient_fields": 7, "custom_geometry": 1, "gantt": 1, "dual_axis": 1}


@pytest.fixture(scope="module")
def rep():
    if not TWBX.exists():
        pytest.skip("Superstore.twbx missing")
    tmp = Path(tempfile.mkdtemp())
    with zipfile.ZipFile(TWBX) as z:
        z.extractall(tmp)
    twb = next(tmp.rglob("*.twb"))
    pages = extract.extract_from_twb(twb, "hyper_raw_data", COLUMNS)
    return report.build_report(pages)


def test_worksheet_and_emitted_counts(rep):
    assert rep["worksheets_total"] == EXPECTED_WORKSHEETS
    assert rep["visuals_emitted"] == EXPECTED_EMITTED
    assert rep["emitted_by_type"] == EXPECTED_BY_TYPE


def test_skip_taxonomy(rep):
    assert rep["skipped_by_bucket"] == EXPECTED_SKIP
    assert rep["visuals_emitted"] + rep["visuals_skipped"] == rep["worksheets_total"]


def test_coverage_is_labeled_not_render_verified(rep):
    assert rep["coverage_pct_schema_valid"] == 34.4
    assert "NOT render-verified" in rep["coverage_label"]
    assert "pending" in rep["render_verified"]
