$ErrorActionPreference = "Continue"

$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDirectory "windows_startup.log"
$startScript = Join-Path $projectRoot "scripts\start_all.py"

if (-not (Test-Path -LiteralPath $logDirectory)) {
    New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null
}

function Write-StartupLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $logPath -Value "[$timestamp] $Message" -Encoding UTF8
}

Write-StartupLog "Daily News Digest Windows startup runner started."
Write-StartupLog "Project root: $projectRoot"

try {
    Set-Location -LiteralPath $projectRoot

    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $python = $venvPython
        Write-StartupLog "Using project venv Python: $python"
    } else {
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $pythonCommand) {
            Write-StartupLog "ERROR: Python was not found. Please create .venv or add Python to PATH."
            exit 1
        }
        $python = $pythonCommand.Source
        Write-StartupLog "Using PATH Python: $python"
    }

    if (-not (Test-Path -LiteralPath $startScript)) {
        Write-StartupLog "ERROR: start_all.py was not found: $startScript"
        exit 1
    }

    Write-StartupLog "Running: $python $startScript"
    $output = & $python $startScript 2>&1
    foreach ($line in $output) {
        Write-StartupLog $line
    }
    $exitCode = $LASTEXITCODE
    Write-StartupLog "start_all.py finished with exit code: $exitCode"
    exit $exitCode
} catch {
    Write-StartupLog "ERROR: $($_.Exception.GetType().Name): $($_.Exception.Message)"
    exit 1
}
