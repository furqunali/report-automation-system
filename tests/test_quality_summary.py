from reporting_core.quality import QualityReport
from reporting_core.quality_summary import summarize_quality


def test_quality_summary_calculates_rates():
    report = QualityReport(10, 2, 5, 2, 123.45)
    result = summarize_quality(report)
    assert result.valid_rate == 0.8
    assert result.invalid_rate == 0.2
    assert result.has_data is True
    assert result.ready_for_export is False


def test_quality_summary_marks_clean_report_ready():
    report = QualityReport(4, 1, 3, 0, 20.0)
    assert summarize_quality(report).ready_for_export is True


def test_quality_summary_handles_empty_report():
    report = QualityReport(0, 0, 0, 0, 0.0)
    assert summarize_quality(report).has_data is False
    assert summarize_quality(report).ready_for_export is False
