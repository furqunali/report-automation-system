from reporting_core.filter_contract import FilterContract
from reporting_core.filter_summary import summarize_filters
def test_summary_contains_only_active_filters():
    filters = FilterContract(site=" North ", category="Hardware")
    assert summarize_filters(filters) == {"site": "North", "category": "Hardware"}
def test_empty_filters_have_empty_summary():
    assert summarize_filters(FilterContract()) == {}
