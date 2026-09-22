from reporting_core.models import ReportRow
from reporting_core.quality import profile_rows


def test_profile_rows_counts_valid_business_dimensions():
    rows = [ReportRow("A","Food","Rice",2,10,"Active"),
            ReportRow("B","Food","Tea",1,5,"Active")]
    report = profile_rows(rows)
    assert report.healthy
    assert report.sites == 2
    assert report.products == 2
    assert report.total_sales == 15

def test_profile_rows_counts_invalid_rows_without_dropping_valid_metrics():
    rows = [ReportRow("A","Food","Rice",2,10,"Active"),
            ReportRow("","","Bad",-1,0,"Active")]
    report = profile_rows(rows)
    assert report.rows == 2
    assert report.invalid_rows == 1
    assert report.total_sales == 10
    assert not report.healthy
