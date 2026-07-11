"""Unit tests for the AST → DAX transpiler.

Each supported pattern has a test; unsupported families assert the taxonomy
category so skip reasons stay precise.
"""

import pytest

from tab2pbi.ir.parser import parse
from tab2pbi.rewrite.dax import TranspileError, to_dax

T = "Orders"


def _annotate(ast, table=T):
    """Attach a table to every field node (simulating context resolution)."""
    from tab2pbi.ir.ast_utils import iter_fields
    for f in iter_fields(ast):
        f["table"] = table
    return ast


def dax(formula, table=T):
    return to_dax(_annotate(parse(formula), table))


def test_single_aggregation_dax():
    assert dax("SUM([Sales])") == "SUM(Orders[Sales])"


def test_countd_maps_to_distinctcount():
    assert dax("COUNTD([Order ID])") == "DISTINCTCOUNT(Orders[Order ID])"


def test_algebraic_ratio():
    assert dax("SUM([Profit]) / SUM([Sales])") == "SUM(Orders[Profit]) / SUM(Orders[Sales])"


def test_number_and_string_constants():
    assert dax("2022") == "2022"
    assert dax('"hello"') == '"hello"'


def test_string_quote_escaping():
    from tab2pbi.rewrite.dax import _dax_string
    assert _dax_string('a"b') == '"a""b"'


def test_if_to_if():
    out = dax('IF [Sales] > 0 THEN "p" ELSE "n" END')
    assert out == 'IF(Orders[Sales] > 0, "p", "n")'


def test_multi_branch_to_switch():
    out = dax('IF [Sales] > 0 THEN "p" ELSEIF [Sales] < 0 THEN "n" ELSE "z" END')
    assert out.startswith("SWITCH(TRUE()")
    assert '"z"' in out


def test_datediff():
    out = dax("DATEDIFF('day',[Order Date],[Ship Date])")
    assert out == "DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)"


def test_year_function():
    assert dax("YEAR([Order Date])") == "YEAR(Orders[Order Date])"


def test_logical_and_or():
    out = dax("IF [Sales] > 0 AND [Profit] > 0 THEN 1 ELSE 0 END")
    assert "&&" in out


def test_window_function_is_table_calc():
    with pytest.raises(TranspileError) as e:
        dax("WINDOW_MAX(SUM([Sales]))")
    assert e.value.taxonomy == "window_fn"


def test_rank_is_table_calc():
    with pytest.raises(TranspileError) as e:
        dax("RANK_UNIQUE(SUM([Sales]))")
    assert e.value.taxonomy == "table_calc"


def test_unresolved_field_raises():
    ast = parse("SUM([Sales])")  # not annotated → no table
    with pytest.raises(TranspileError) as e:
        to_dax(ast)
    assert e.value.taxonomy == "unresolved"


def test_unknown_function_is_unsupported_fn():
    with pytest.raises(TranspileError) as e:
        dax("STR([Sales])")
    assert e.value.taxonomy == "unsupported_fn"
