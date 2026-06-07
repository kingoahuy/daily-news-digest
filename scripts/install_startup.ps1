$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$startupDirectory = [Environment]::GetFolderPath("Startup")
$launcherPath = Join-Path $startupDirectory "DailyNewsDigest.cmd"
$startScript = Join-Path $projectRoot "scripts\start_all.py"

$content = @"
@echo off
cd /d "$projectRoot"
"$python" "$startScript" >nul 2>&1
"@

Set-Content -LiteralPath $launcherPath -Value $content -Encoding ASCII
Write-Output "Startup launcher installed: $launcherPath"
Write-Output "FastAPI and Next.js will be restored after the next Windows sign-in."
