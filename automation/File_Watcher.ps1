# File_Watcher.ps1 - auto-process whenever a report is added to 01_input_reports.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Input = Join-Path $Root "01_input_reports"

Write-Host "👀 Watching: $Input" -ForegroundColor Cyan
Write-Host "Add a .csv/.xlsx file to auto-process. Press Ctrl+C to stop.`n"

$fsw = New-Object System.IO.FileSystemWatcher $Input
$fsw.Filter = "*.*"
$fsw.EnableRaisingEvents = $true

Register-ObjectEvent $fsw Created -SourceIdentifier ReportAdded -Action {
    Start-Sleep -Seconds 2   # let the file finish copying
    Write-Host "New file detected: $($Event.SourceEventArgs.Name)" -ForegroundColor Yellow
    python "$using:Root\process_reports.py"
} | Out-Null

try { while ($true) { Start-Sleep -Seconds 1 } }
finally { Unregister-Event -SourceIdentifier ReportAdded }
