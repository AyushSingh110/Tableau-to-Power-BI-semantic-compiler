"""Unit tests for the marks extractor (field resolution, real-world names)."""

from tab2pbi.visual.extract import _to_fieldref, parse_encoded_ref

# The flat spike model's columns (Superstore), including spaces/slashes/hyphens.
COLUMNS = [
    "Order ID", "Order Date", "Ship Date", "Ship Mode", "Customer Name", "Segment",
    "Country/Region", "City", "State", "Postal Code", "Region", "Category",
    "Sub-Category", "Product Name", "Sales", "Quantity", "Discount", "Profit",
]
COLS_LC = {c.lower(): c for c in COLUMNS}


def test_parse_encoded_ref():
    assert parse_encoded_ref("[ds].[sum:Sales:qk]") == ("sum", "Sales", "qk")
    assert parse_encoded_ref("[ds].[none:State:nk]") == ("none", "State", "nk")
    assert parse_encoded_ref("[ds].[Geometry (generated)]") == (None, "Geometry (generated)", None)


def test_resolve_measure_and_dimension():
    fr, bad = _to_fieldref("[ds].[sum:Sales:qk]", "hyper_raw_data", COLS_LC)
    assert bad is None and fr.is_measure and fr.column == "Sales" and fr.aggregation == "sum"
    fr, bad = _to_fieldref("[ds].[none:State:nk]", "hyper_raw_data", COLS_LC)
    assert bad is None and not fr.is_measure and fr.column == "State"


def test_resolve_realworld_column_names():
    # refinement #2: spaces / slashes / hyphens must resolve to the exact column
    for ref, expect in [
        ("[ds].[none:Sub-Category:nk]", "Sub-Category"),
        ("[ds].[none:Country/Region:nk]", "Country/Region"),
        ("[ds].[tmn:Order Date:qk]", "Order Date"),
        ("[ds].[sum:Postal Code:qk]", "Postal Code"),
    ]:
        fr, bad = _to_fieldref(ref, "hyper_raw_data", COLS_LC)
        assert bad is None and fr.column == expect


def test_unresolved_field_is_unmapped_not_guessed():
    fr, bad = _to_fieldref("[ds].[usr:Calculation_123:nk]", "hyper_raw_data", COLS_LC)
    assert fr is None and "no matching model column" in bad["reason"]
    fr, bad = _to_fieldref("[ds].[:Measure Names]", "hyper_raw_data", COLS_LC)
    assert fr is None and bad is not None
