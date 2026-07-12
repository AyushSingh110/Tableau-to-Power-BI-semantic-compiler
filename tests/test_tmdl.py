"""Unit tests for the TMDL semantic-model emitter."""

from tab2pbi.export import tmdl

HYPER = [
    {"schema": "Extract", "table": "Orders", "columns": [
        {"column_name": "State", "data_type": "TEXT"},
        {"column_name": "Sales", "data_type": "DOUBLE"},
        {"column_name": "Order Date", "data_type": "DATE"},
    ]},
    {"schema": "Extract", "table": "People", "columns": [
        {"column_name": "Region", "data_type": "TEXT"},
    ]},
]
FINAL = {
    "measures": {"[Ratio]": "SUM(Orders[Profit]) / SUM(Orders[Sales])"},
    "measure_table_map": {"[Ratio]": "Orders"},
    "calculated_columns": [{"name": "[Delay]", "table": "Orders", "dax": "DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)"}],
    "parameters": [
        {"name": "[P1]", "table": "Orders", "dax": "2022", "note": "Tableau parameter"},
        {"name": "[Multi]", "table": "Orders", "dax": "line1\nline2", "note": "Tableau parameter"},
    ],
}
INFERRED = {"relationships": [
    {"from_table": "Orders", "from_column": "Region", "to_table": "People",
     "to_column": "Region", "cardinality": "ManyToOne"},
]}


def test_emits_full_folder(tmp_path):
    info = tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    defn = tmp_path / "M.SemanticModel" / "definition"
    for f in ("model.tmdl", "database.tmdl", "relationships.tmdl", "cultures/en-US.tmdl",
              "tables/Orders.tmdl", "tables/People.tmdl"):
        assert (defn / f).exists()
    assert (tmp_path / "M.SemanticModel" / "definition.pbism").exists()
    assert info["tables"] == 2 and info["measures"] == 1 and info["relationships"] == 1


def test_model_refs_and_no_time_intelligence(tmp_path):
    tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    model = (tmp_path / "M.SemanticModel/definition/model.tmdl").read_text(encoding="utf-8")
    assert "ref table Orders" in model and "ref table People" in model
    assert "__PBI_TimeIntelligenceEnabled = 0" in model


def test_table_has_columns_measure_calc_partition(tmp_path):
    tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    t = (tmp_path / "M.SemanticModel/definition/tables/Orders.tmdl").read_text(encoding="utf-8")
    assert "column 'Order Date'\n\t\tdataType: dateTime" in t  # data column, reference shape
    assert "measure Ratio = SUM(Orders[Profit]) / SUM(Orders[Sales])" in t
    assert "column Delay = DATEDIFF(" in t
    assert "column P1 = 2022" in t
    assert "partition Orders = m" in t and "Csv.Document(File.Contents(" in t


def test_multiline_expression_is_skipped_not_emitted(tmp_path):
    info = tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    t = (tmp_path / "M.SemanticModel/definition/tables/Orders.tmdl").read_text(encoding="utf-8")
    assert "line1" not in t and "line2" not in t                 # not emitted
    assert info["parameters"] == 1                                # only P1
    assert any(s["name"] == "Multi" for s in info["skipped_multiline"])


def test_relationship_shape(tmp_path):
    tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    r = (tmp_path / "M.SemanticModel/definition/relationships.tmdl").read_text(encoding="utf-8")
    assert "fromColumn: Orders.Region" in r and "toColumn: People.Region" in r


def test_absolute_csv_path(tmp_path):
    tmdl.run(HYPER, FINAL, INFERRED, tmp_path / "M.SemanticModel", tmp_path)
    t = (tmp_path / "M.SemanticModel/definition/tables/Orders.tmdl").read_text(encoding="utf-8")
    # The raw absolute path is baked in verbatim (single OS separators), exactly
    # as Power BI writes it. Power Query M treats "\" as literal, so it must NOT
    # be escaped to "\\". Regression guard for the double-backslash bug.
    assert str(tmp_path) in t
    if "\\" in str(tmp_path):  # Windows
        assert "\\\\" not in t
