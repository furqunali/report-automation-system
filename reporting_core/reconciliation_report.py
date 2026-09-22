"""Stable JSON export for reconciliation health summaries."""
from __future__ import annotations

import json
from dataclasses import asdict

from reporting_core.reconciliation_health import ReconciliationHealth
from reporting_core.reconciliation_report_schema import validate_reconciliation_report


def reconciliation_report_dict(result: ReconciliationHealth) -> dict:
    if not isinstance(result, ReconciliationHealth):
        raise TypeError("result must be a ReconciliationHealth")
    payload = asdict(result)
    if not validate_reconciliation_report(payload):
        raise ValueError("reconciliation report failed schema validation")
    return payload

def reconciliation_report_json(result: ReconciliationHealth) -> str:
    return json.dumps(reconciliation_report_dict(result), sort_keys=True)
