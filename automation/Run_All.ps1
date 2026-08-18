# Run_All.ps1 - process all reports, then open the dashboard.
# Portable: resolves the project root relative to this script (no hard-coded paths).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  RUNNING FULL AUTOMATION" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nStep 1: Processing reports..." -ForegroundColor Yellow
python "$Root\process_reports.py"

Write-Host "`nStep 2: Opening dashboard..." -ForegroundColor Yellow
Start-Process "$Root\dashboard\dashboard.html"

Write-Host "`n✅ AUTOMATION COMPLETE" -ForegroundColor Green
Write-Host "Input : $Root\01_input_reports"
Write-Host "Output: $Root\03_output"
