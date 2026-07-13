param(
    [double]$Hours = 3.0,
    [int]$Seconds = 0
)

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Error "Local .venv Python not found at $venvPython"
    exit 1
}

Set-Location $repoRoot

if ($Seconds -gt 0) {
    & $venvPython "tests\endurance_soak.py" --seconds $Seconds
} else {
    & $venvPython "tests\endurance_soak.py" --hours $Hours
}
