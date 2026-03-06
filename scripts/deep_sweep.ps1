param(
  [string]$OutDir = "outputs\checks"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "[deep-sweep] compile check"
python -m compileall src tests | Out-Null

Write-Host "[deep-sweep] run full pytest"
python -m pytest --basetemp C:/Users/max/AppData/Roaming/Python/Python313/pytest-tmp

Write-Host "[deep-sweep] run contract checks"
python scripts\run_contract_checks.py

Write-Host "[deep-sweep] run reproducibility checks"
python scripts\run_repro_check.py

"ok" | Set-Content -Path (Join-Path $OutDir "deep_sweep.ok") -Encoding UTF8
Write-Host "[deep-sweep] success"
