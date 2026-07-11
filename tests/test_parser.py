"""Unit tests for the Tableau calc tokenizer + parser."""


from tab2pbi.ir.parser import build_ast, parse


def test_single_aggregation():
    ast = parse("SUM([Sales])")
    assert ast == {"node": "aggregation", "agg": "SUM",
                   "arg": {"node": "field", "name": "Sales"}}


def test_binary_of_aggregations():
    ast = parse("SUM([Profit]) / SUM([Sales])")
    assert ast["node"] == "binary"
    assert ast["op"] == "/"
    assert ast["left"]["agg"] == "SUM" and ast["right"]["agg"] == "SUM"


def test_number_and_string_constants():
    assert parse("2022") == {"node": "constant", "dtype": "number", "value": 2022}
    assert parse('"hi"') == {"node": "constant", "dtype": "string", "value": "hi"}


def test_url_in_string_is_not_a_comment():
    # `//` inside a string must survive tokenization.
    ast = parse('"see https://example.com/x"')
    assert ast["value"] == "see https://example.com/x"


def test_field_datasource_qualified():
    ast = parse("[Parameters].[Parameter 1]")
    assert ast == {"node": "field", "name": "Parameter 1"}


def test_if_elseif_else():
    ast = parse('IF [x] > 0 THEN "p" ELSEIF [x] < 0 THEN "n" ELSE "z" END')
    assert ast["node"] == "conditional"
    assert len(ast["branches"]) == 2
    assert ast["otherwise"]["value"] == "z"


def test_case_normalized_to_conditional():
    ast = parse("CASE [x] WHEN 1 THEN 'a' WHEN 2 THEN 'b' END")
    assert ast["node"] == "conditional"
    assert ast["branches"][0]["when"]["node"] == "comparison"


def test_function_call_and_datediff():
    ast = parse("DATEDIFF('day',[Order Date],[Ship Date])")
    assert ast["node"] == "function" and ast["name"] == "DATEDIFF"
    assert len(ast["args"]) == 3


def test_lod_is_unsupported_not_crash():
    ast = parse("{ FIXED [Region] : SUM([Sales]) }")
    assert ast == {"node": "unsupported", "reason": "lod_expression"}


def test_comments_stripped_outside_strings():
    ast = parse("SUM([Sales]) // total sales")
    assert ast["node"] == "aggregation"


def test_build_ast_never_raises_on_garbage():
    ast = build_ast("SUM(((")
    assert ast["node"] == "parse_error"
    assert ast["formula"] == "SUM((("


def test_build_ast_empty():
    assert build_ast("   ")["reason"] == "empty_formula"
