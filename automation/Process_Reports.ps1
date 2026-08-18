# Process_Reports.ps1 - process reports only (no dashboard launch).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
python "$Root\process_reports.py"
