from reporting_core.run_policy import RunFinding
from reporting_core.run_policy_summary import summarize_run


def test_run_policy_summary_counts_findings():
    findings = (RunFinding("INVALID_ROWS", "error", "invalid"), RunFinding("EMPTY_RUN", "warning", "empty"))
    summary = summarize_run(findings)
    assert summary.total == 2
    assert summary.errors == 1
    assert summary.warnings == 1
    assert summary.infos == 0
    assert not summary.healthy
