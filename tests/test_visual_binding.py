"""Coherent multi-table binding: fields resolve to their real owning table."""

from tab2pbi.visual.extract import multitable_resolver

# Minimal logical->physical mapping (State/Sales in Orders, Region in both).
MAPPINGS = [
    {"logical_field": "State", "physical_column": "State", "table": "Orders_ECFCA"},
    {"logical_field": "Sales", "physical_column": "Sales", "table": "Orders_ECFCA"},
    {"logical_field": "Region", "physical_column": "Region", "table": "Orders_ECFCA"},
    {"logical_field": "Region", "physical_column": "Region", "table": "People_D730"},
    {"logical_field": "Regional Manager", "physical_column": "Regional Manager", "table": "People_D730"},
]
TABLES = {"Orders_ECFCA": {"type": "fact"}, "People_D730": {"type": "dimension"}}


def test_resolves_to_real_entity_not_flat():
    r = multitable_resolver(MAPPINGS, TABLES)
    assert r("State") == ("Orders_ECFCA", "State")
    assert r("Sales") == ("Orders_ECFCA", "Sales")
    assert r("Regional Manager") == ("People_D730", "Regional Manager")


def test_ambiguous_field_prefers_fact_table():
    r = multitable_resolver(MAPPINGS, TABLES)
    # Region exists in both; fact (Orders) is preferred.
    assert r("Region") == ("Orders_ECFCA", "Region")


def test_unresolved_field_returns_none_not_guess():
    r = multitable_resolver(MAPPINGS, TABLES)
    assert r("Calculation_123") is None
    assert r("Measure Names") is None
