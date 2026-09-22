"""Stable JSON contract for report run policy findings."""
from __future__ import annotations

import json
from dataclasses import asdict

from reporting_core.run_policy import RunFinding


def to_json(findings: tuple[RunFinding, ...]) -> str:
    return json.dumps([asdict(finding) for finding in findings], sort_keys=True, separators=(",", ":"))
