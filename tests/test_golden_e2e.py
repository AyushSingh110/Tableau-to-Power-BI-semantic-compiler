"""Golden end-to-end test on the Superstore workbook.

This test locks the pipeline's stable invariants so that the higher-risk parser
rewrite (regex AST builder -> tokenizer/parser) cannot silently regress
existing output. The anchors that must NEVER change:

- 3 physical tables, fact table = Orders (by size heuristic);
- the Profit/Sales ratio converts to one exact, table-qualified DAX string;
- exactly one data-driven relationship: Orders.Region -> People.Region;
- no measure is silently lost (converted + skipped == total).

The *counts* of converted/skipped measures are asserted as a snapshot that is
intentionally updated (in the same commit) whenever a new transpiler pattern is
added. The anchor measure and the relationship are exact and stay green
throughout.
"""

ORDERS = "Orders_ECFCA1FB690A41FE803BC071773BA862"
PEOPLE = "People_D73023733B004CC1B3CB1ACF62F4A965"
PROFIT_RATIO = "[Calculation_1368249927221915648]"

# Snapshot of current conversion counts. Update deliberately when coverage grows.
EXPECTED_MEASURES = 1
EXPECTED_COLUMNS = 1
EXPECTED_PARAMETERS = 4
EXPECTED_TOTAL = 17


def test_tables_and_fact(superstore_artifacts):
    tables = superstore_artifacts["final"]["tables"]
    assert set(tables) == {
        ORDERS,
        PEOPLE,
        "Returns_2AA0FE4D737A4F63970131D0E7480A03",
    }
    assert tables[ORDERS]["type"] == "fact"
    assert tables[PEOPLE]["type"] == "dimension"


def test_anchor_measure_dax_exact(superstore_artifacts):
    """The known-good measure must always transpile to this exact DAX."""
    converted = superstore_artifacts["converted"]["measures"]
    assert converted.get(PROFIT_RATIO) == (
        f"SUM({ORDERS}[Profit]) / SUM({ORDERS}[Sales])"
    )


def test_relationship_inferred_exact(superstore_artifacts):
    rels = superstore_artifacts["inferred"]["relationships"]
    assert len(rels) == 1
    r = rels[0]
    assert (r["from_table"], r["from_column"]) == (ORDERS, "Region")
    assert (r["to_table"], r["to_column"]) == (PEOPLE, "Region")
    assert r["cardinality"] == "ManyToOne"
    assert r["confidence"] == 1.0


def test_no_calc_silently_dropped(superstore_artifacts):
    report = superstore_artifacts["final"]["conversion_report"]
    accounted = (
        report["measures_converted"]
        + report["columns_converted"]
        + report["parameters_converted"]
        + report["skipped_count"]
    )
    assert accounted == report["total_calculations"]
    # every skipped calculation carries a reason and a taxonomy bucket
    assert all(s.get("reason") and s.get("taxonomy") for s in report["skipped_measures"])


def test_conversion_count_snapshot(superstore_artifacts):
    report = superstore_artifacts["final"]["conversion_report"]
    assert report["total_calculations"] == EXPECTED_TOTAL
    assert report["measures_converted"] == EXPECTED_MEASURES
    assert report["columns_converted"] == EXPECTED_COLUMNS
    assert report["parameters_converted"] == EXPECTED_PARAMETERS


def test_tom_is_wellformed(superstore_artifacts):
    tom = superstore_artifacts["tom"]
    assert tom["compatibilityLevel"] == 1567
    model = tom["model"]
    assert {t["name"] for t in model["tables"]} == {
        ORDERS,
        PEOPLE,
        "Returns_2AA0FE4D737A4F63970131D0E7480A03",
    }
    # the anchor measure is placed on the Orders table
    orders = next(t for t in model["tables"] if t["name"] == ORDERS)
    assert any(m["name"] == PROFIT_RATIO for m in orders["measures"])
