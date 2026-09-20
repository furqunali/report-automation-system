from reporting_core.run_health import RunHealth
from reporting_core.run_health_json import to_json

def test_run_health_json_is_stable():
    health = RunHealth("healthy", 1.0, 0.0, False)
    assert to_json(health) == '{"actionable":false,"error_rate":0.0,"status":"healthy","valid_rate":1.0}'
