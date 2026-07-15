"""Unit tests for the pandas reference evaluator."""

import pandas as pd
import pytest

from tab2pbi.evaluation import NotEvaluable, evaluate
from tab2pbi.ir.parser import parse

TABLES = {"Orders": pd.DataFrame({"Profit": [10.0, 20.0, 30.0], "Sales": [100.0, 100.0, 200.0]})}


def _annotate(ast, table="Orders"):
    from tab2pbi.ir.ast_utils import iter_fields
    for f in iter_fields(ast):
        f["table"] = table
    return ast


def test_sum():
    assert evaluate(_annotate(parse("SUM([Profit])")), TABLES) == 60.0


def test_ratio():
    got = evaluate(_annotate(parse("SUM([Profit]) / SUM([Sales])")), TABLES)
    assert got == pytest.approx(60.0 / 400.0)


def test_constant():
    assert evaluate(parse("2022"), TABLES) == 2022.0


def test_conditional_not_evaluable():
    with pytest.raises(NotEvaluable):
        evaluate(_annotate(parse('IF [Profit] > 0 THEN 1 ELSE 0 END')), TABLES)


def test_conditional_aggregation_sumx():
    tables = {"Orders": pd.DataFrame({
        "Sales": [10.0, 20.0, 30.0],
        "Order Date": ["2022-01-01", "2021-01-01", "2022-06-01"],
    })}
    ast = _annotate(parse("SUM(ZN(IF YEAR([Order Date])=2022 THEN [Sales] ELSE 0 END))"))
    assert evaluate(ast, tables) == 40.0   # 10 + 30 (2022 rows only)
