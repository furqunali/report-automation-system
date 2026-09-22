import pytest

from reporting_core.export_contract import ExportContract, build_export_contract


def test_export_contract_rounds_sales_and_preserves_rows():
    contract = build_export_contract([{"site":"A","sales":10}], 10.126)
    assert contract.as_dict()["total_sales"] == 10.13
    assert contract.row_count == 1

def test_row_count_must_match_payload():
    with pytest.raises(ValueError):
        ExportContract("1", tuple(), 0, 1)

def test_negative_sales_rejected():
    with pytest.raises(ValueError):
        build_export_contract([], -1)

def test_rows_are_copied():
    rows=[{"site":"A"}]
    contract=build_export_contract(rows,0)
    rows[0]["site"]="B"
    assert contract.rows[0]["site"]=="A"
