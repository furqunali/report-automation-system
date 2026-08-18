# Create_Scheduled_Task.ps1 - schedule a daily 8 AM automated run.
# Run this once from an elevated (Administrator) PowerShell.
$ErrorActionPreference = "Stop"
$Root   = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $PSScriptRoot "Run_All.ps1"

$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
             -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 8am

Register-ScheduledTask -TaskName "ReportAutomationSystem" `
    -Action $action -Trigger $trigger -Force `
    -Description "Daily consolidation of store reports into the dashboard."

Write-Host "✅ Scheduled 'ReportAutomationSystem' to run daily at 8:00 AM." -ForegroundColor Green
