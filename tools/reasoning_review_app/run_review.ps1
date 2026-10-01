$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

Write-Host "KODAAI Reasoning Review baslatiliyor..." -ForegroundColor Cyan
Write-Host "http://127.0.0.1:8091" -ForegroundColor Green
& $Python (Join-Path $PSScriptRoot "app.py")
