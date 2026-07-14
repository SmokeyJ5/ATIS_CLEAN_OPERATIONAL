Write-Host "Running ATIS regression smoke test..."
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
	& $venvPython "scripts\check_manifest_cleanliness.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	& $venvPython "tests\regression_smoke.py"
} else {
	Write-Warning "Local .venv Python not found, falling back to ambient python."
	python "scripts\check_manifest_cleanliness.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	python "tests\regression_smoke.py"
}
