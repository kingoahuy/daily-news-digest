$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$taskName = "DailyNewsDigestLocalServices"
$runnerScript = Join-Path $projectRoot "scripts\startup_runner.ps1"
$startupDirectory = [Environment]::GetFolderPath("Startup")
$legacyLauncherPath = Join-Path $startupDirectory "DailyNewsDigest.cmd"

if (-not (Test-Path -LiteralPath $runnerScript)) {
    throw "startup_runner.ps1 was not found: $runnerScript"
}

if (Test-Path -LiteralPath $legacyLauncherPath) {
    Remove-Item -LiteralPath $legacyLauncherPath -Force
    Write-Output "Removed legacy Startup launcher: $legacyLauncherPath"
}

$powerShell = (Get-Command powershell.exe).Source
$action = New-ScheduledTaskAction -Execute $powerShell -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runnerScript`"" -WorkingDirectory $projectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel LeastPrivilege
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -StartWhenAvailable

$task = New-ScheduledTask -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Start Daily News Digest FastAPI, Next.js and local scheduler after Windows sign-in."
Register-ScheduledTask -TaskName $taskName -InputObject $task -Force | Out-Null

Write-Output "Windows startup scheduled task installed: $taskName"
Write-Output "It will run after the next Windows sign-in."
Write-Output "To start immediately, run:"
Write-Output "python scripts/start_all.py"
Write-Output "Startup log: logs/windows_startup.log"
