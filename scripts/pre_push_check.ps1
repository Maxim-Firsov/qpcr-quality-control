$ErrorActionPreference = "Stop"

Write-Host "[pre-push] running deep sweep"
powershell -ExecutionPolicy Bypass -File scripts\deep_sweep.ps1

Write-Host "[pre-push] success"
