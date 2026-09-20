from reporting_core.run_policy import RunFinding
from reporting_core.run_policy_summary import summarize_run

def test_run_policy_summary_counts_findings():
    findings = (RunFinding("INVALID_ROWS", "error", "invalid"), RunFinding("EMPTY_RUN", "warning", "empty"))
    assert summarize_run(findings) == (2, 1, 1, 0, False)
