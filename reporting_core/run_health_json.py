"""Stable JSON contract for report run health."""
from __future__ import annotations
from dataclasses import asdict
import json
from reporting_core.run_health import RunHealth

def to_json(health: RunHealth) -> str:
    return json.dumps(asdict(health), sort_keys=True, separators=(",", ":"))
