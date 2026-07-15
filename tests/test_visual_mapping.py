"""Unit tests for the deterministic mark -> visual mapping table."""

from tab2pbi.visual.ir import FieldRef
from tab2pbi.visual.mapping import classify

DIM = FieldRef("hyper_raw_data", "Category", None)
GEO = FieldRef("hyper_raw_data", "State", None)
M1 = FieldRef("hyper_raw_data", "Sales", "sum")
M2 = FieldRef("hyper_raw_data", "Profit", "sum")


def test_bar_to_columnchart():
    p = classify("Bar", [DIM], [M1])
    assert p.visual_type == "columnChart"
    assert p.wells["Category"] == [DIM] and p.wells["Y"] == [M1]


def test_pie_line_area():
    assert classify("Pie", [DIM], [M1]).visual_type == "pieChart"
    assert classify("Line", [DIM], [M1]).visual_type == "lineChart"
    assert classify("Area", [DIM], [M1]).visual_type == "areaChart"


def test_scatter_needs_two_measures():
    # refinement #4: one measure must NOT emit a broken scatter
    assert classify("Circle", [DIM], [M1]).skip_reason == "insufficient_fields"
    p = classify("Circle", [DIM], [M1, M2])
    assert p.visual_type == "scatterChart"
    assert p.wells["X"] == [M1] and p.wells["Y"] == [M2]


def test_geo_bubble_map():
    p = classify("Multipolygon", [GEO], [M1], geo_standard_dim=GEO)
    assert p.visual_type == "map"
    assert p.wells["Category"] == [GEO] and p.wells["Size"] == [M1]


def test_generated_geometry_skips():
    p = classify("Multipolygon", [], [M1], generated_geometry=True)
    assert p.skip_reason == "custom_geometry"


def test_generated_geometry_with_standard_dim_emits_map():
    # Generated lat/long on a standard region (State) is a bubble map, not a skip.
    p = classify("Multipolygon", [GEO], [M1], geo_standard_dim=GEO, generated_geometry=True)
    assert p.visual_type == "map"
    assert p.wells["Category"] == [GEO] and p.wells["Size"] == [M1]


def test_dims_only_text_is_detail_table():
    d2 = FieldRef("hyper_raw_data", "Segment", None)
    p = classify("Text", [DIM, d2], [])
    assert p.visual_type == "tableEx" and p.wells["Values"] == [DIM, d2]


def test_single_dim_text_still_skips():
    # one dim + no measure = a KPI whose value is an unconverted calc -> keep skip
    assert classify("Text", [GEO], []).skip_reason == "insufficient_fields"


def test_map_without_standard_region_skips():
    p = classify("Multipolygon", [DIM], [M1])  # no geo_standard_dim
    assert p.skip_reason == "custom_geometry"


def test_hard_skips():
    assert classify("GanttBar", [DIM], [M1]).skip_reason == "gantt"
    assert classify("Shape", [DIM], [M1]).skip_reason == "custom_shape"
    assert classify("Bar", [DIM], [M1], multi_mark=True).skip_reason == "dual_axis"


def test_card_and_table():
    assert classify("Text", [], [M1]).visual_type == "card"
    assert classify("Text", [DIM], [M1]).visual_type == "tableEx"


def test_insufficient_and_unsupported():
    assert classify("Bar", [DIM], []).skip_reason == "insufficient_fields"
    assert classify("Gauge", [DIM], [M1]).skip_reason == "unsupported_mark"
