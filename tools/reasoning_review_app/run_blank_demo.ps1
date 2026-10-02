$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

& $Python (Join-Path $PSScriptRoot "generate_blank_demo.py")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$Mp3 = Join-Path $Root "artifacts\tts_demos\blank_emphasis_alloy_v1.mp3"
if (Test-Path $Mp3) {
    Write-Host "Caliniyor: $Mp3" -ForegroundColor Green
    Start-Process $Mp3
}
