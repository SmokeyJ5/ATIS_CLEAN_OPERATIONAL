Write-Host "Running ATIS regression smoke test..."
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
	& $venvPython "scripts\find_todos.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	& $venvPython "scripts\check_manifest_cleanliness.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	& $venvPython -m pytest -q
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
	Write-Warning "Local .venv Python not found, falling back to ambient python."
	python "scripts\find_todos.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	python "scripts\check_manifest_cleanliness.py"
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
	python -m pytest -q
	if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
