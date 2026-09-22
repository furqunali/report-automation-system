from reporting_core.run_health import RunHealth
from reporting_core.run_policy import evaluate_run


def test_run_policy_reports_invalid_rows():
    findings = evaluate_run(RunHealth("degraded", 0.8, 0.2, True))
    assert findings[0].code == "INVALID_ROWS"
    assert findings[0].severity == "error"

def test_run_policy_reports_healthy_run():
    assert evaluate_run(RunHealth("healthy", 1.0, 0.0, False))[0].code == "HEALTHY"
