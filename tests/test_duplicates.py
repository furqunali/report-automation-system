from reporting_core.duplicates import duplicate_row_indices
from reporting_core.models import ReportRow


def row(site="A", product="Widget", sales=10.0):
    return ReportRow(site, "Retail", product, 1, sales, "Active")


def test_duplicate_row_indices_groups_exact_duplicates():
    result = duplicate_row_indices([row(), row(), row(product="Other")])
    assert list(result.values()) == [[0, 1]]


def test_duplicate_row_indices_ignores_distinct_rows():
    assert duplicate_row_indices([row(), row(sales=11.0)]) == {}
