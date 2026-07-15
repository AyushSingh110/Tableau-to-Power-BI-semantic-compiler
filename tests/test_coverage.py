"""Integration tests for the coverage-raising converters.

Exercise the whole context → rewrite flow: parameter inlining, conditional
aggregation (SUMX), and calc-to-calc measure references.
"""

from tab2pbi.ir import context
from tab2pbi.ir.parser import build_ast
from tab2pbi.rewrite import dax

TABLES = {"Orders": {"type": "fact", "columns": ["Sales", "Order Date"]}}
MAPPINGS = [
    {"logical_field": "Sales", "physical_column": "Sales", "table": "Orders"},
    {"logical_field": "Order Date", "physical_column": "Order Date", "table": "Orders"},
]
PROV = {"fact_table_inference": {"table": "Orders", "method": "inferred_by_size"}}


def _model(measures):
    return {"tables": TABLES, "provenance": PROV,
            "measures": {n: {"ast": build_ast(f), "formula": f} for n, f in measures.items()}}


def test_parameter_inlined_conditional_aggregation(tmp_path):
    sm = _model({
        "[Yr]": "2022",
        "[YoY]": "SUM(ZN(IF YEAR([Order Date])=[Yr] THEN [Sales] ELSE NULL END))",
    })
    context.run(sm, MAPPINGS, tmp_path)
    out = dax.run(sm, tmp_path)
    assert "[YoY]" in out["measures"]
    d = out["measures"]["[YoY]"]
    assert d.startswith("SUMX(Orders,")          # aggregation over expression
    assert "= 2022" in d                          # parameter inlined to its value
    assert "COALESCE(" in d                       # ZN -> COALESCE(.,0)


def test_calc_to_calc_reference(tmp_path):
    sm = _model({
        "[A]": "SUM([Sales])",
        "[B]": 'IF [A] > 0 THEN "pos" ELSE "neg" END',
    })
    context.run(sm, MAPPINGS, tmp_path)
    out = dax.run(sm, tmp_path)
    assert "[A]" in out["measures"] and "[B]" in out["measures"]
    assert out["measures"]["[B]"] == 'IF([A] > 0, "pos", "neg")'   # references measure A


def test_calc_to_calc_only_if_dependency_converts(tmp_path):
    # B references A, but A is an impossible table-calc -> B must stay skipped.
    sm = _model({
        "[A]": "RANK_UNIQUE(SUM([Sales]),'desc')",
        "[B]": 'IF [A] > 0 THEN "pos" ELSE "neg" END',
    })
    context.run(sm, MAPPINGS, tmp_path)
    out = dax.run(sm, tmp_path)
    assert "[A]" not in out["measures"] and "[B]" not in out["measures"]
    assert {s["calculation_name"] for s in out["skipped_measures"]} == {"[A]", "[B]"}
