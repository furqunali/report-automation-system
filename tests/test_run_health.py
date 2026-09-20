from reporting_core.run_health import assess_run
from reporting_core.run_summary import build_run_summary

def test_run_health_classifies_successful_run():
    health = assess_run(build_run_summary(10, 10, 0, 120.0))
    assert health.status == "healthy"
    assert health.valid_rate == 1.0
    assert not health.actionable

def test_run_health_marks_invalid_rows_actionable():
    health = assess_run(build_run_summary(10, 8, 2, 120.0))
    assert health.status == "degraded"
    assert health.error_rate == 0.2
    assert health.actionable
