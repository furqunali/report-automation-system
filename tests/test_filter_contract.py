from reporting_core.filter_contract import FilterContract, matches_filters


class Row:
    site="A"
    category="Shoes"
    product="Runner"

def test_filter_contract_matches_selected_dimensions():
    assert matches_filters(Row(),FilterContract(site=" A ",product="Runner"))

def test_filter_contract_rejects_mismatched_dimension():
    assert not matches_filters(Row(),FilterContract(category="B"))
