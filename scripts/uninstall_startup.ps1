$startupDirectory = [Environment]::GetFolderPath("Startup")
$launcherPath = Join-Path $startupDirectory "DailyNewsDigest.cmd"

if (Test-Path -LiteralPath $launcherPath) {
    Remove-Item -LiteralPath $launcherPath
    Write-Output "Startup launcher removed: $launcherPath"
} else {
    Write-Output "Daily News Digest startup launcher was not found."
}
