from reporting_core.filter_audit import canonical_filter_key
from reporting_core.filter_contract import FilterContract

def test_filter_key_is_canonical():
    assert canonical_filter_key(FilterContract(site=" North ",product="Widget"))=="site=North;product=Widget"

def test_empty_filter_key():
    assert canonical_filter_key(FilterContract())==""
