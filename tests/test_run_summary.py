import pytest

from reporting_core.run_summary import build_run_summary


def test_run_summary_success():
    result=build_run_summary(3,3,0,12.345)
    assert result.rows_received == 3
    assert result.total_sales == 12.35
    assert result.successful

def test_run_summary_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        build_run_summary(3,2,0,10)
