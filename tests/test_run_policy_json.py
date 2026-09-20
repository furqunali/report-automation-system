from reporting_core.run_policy import RunFinding
from reporting_core.run_policy_json import to_json

def test_run_policy_json_is_stable():
    findings = (RunFinding("INVALID_ROWS", "error", "invalid row rate is 0.2500"),)
    assert to_json(findings) == '[{"code":"INVALID_ROWS","message":"invalid row rate is 0.2500","severity":"error"}]'
