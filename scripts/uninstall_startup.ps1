$ErrorActionPreference = "Continue"

$taskName = "DailyNewsDigestLocalServices"
$startupDirectory = [Environment]::GetFolderPath("Startup")
$legacyLauncherPath = Join-Path $startupDirectory "DailyNewsDigest.cmd"
$removed = $false

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $task) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Output "Windows startup scheduled task removed: $taskName"
    $removed = $true
}

if (Test-Path -LiteralPath $legacyLauncherPath) {
    Remove-Item -LiteralPath $legacyLauncherPath -Force
    Write-Output "Legacy Startup launcher removed: $legacyLauncherPath"
    $removed = $true
}

if (-not $removed) {
    Write-Output "Daily News Digest Windows startup entry was not found."
}
