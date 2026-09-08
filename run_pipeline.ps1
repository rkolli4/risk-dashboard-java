$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$build = Join-Path $root "build"
$data = Join-Path $root "data"
New-Item -ItemType Directory -Force -Path $build, $data | Out-Null

function Assert-Command([string]$name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Required command '$name' was not found on PATH. Install it and retry."
    }
}

Assert-Command "python"
Assert-Command "gcc"
Assert-Command "javac"
Assert-Command "java"

Write-Host "[1/4] Fetching market snapshot"
python (Join-Path $root "src/python/ingest_nifty.py")

Write-Host "[2/4] Building native risk engine"
gcc -std=c11 -O2 -Wall -Wextra -Wpedantic (Join-Path $root "src/c/risk_engine.c") -o (Join-Path $build "risk_engine.exe")

Write-Host "[3/4] Evaluating risk"
& (Join-Path $build "risk_engine.exe") (Join-Path $data "market_snapshot.json") (Join-Path $data "risk_result.json")

Write-Host "[4/4] Starting live Python dashboard"
$classes = Join-Path $build "classes"
New-Item -ItemType Directory -Force -Path $classes | Out-Null
javac -d $classes (Join-Path $root "src/java/RiskUiApp.java")
$port = if ($env:PORT) { $env:PORT } else { "8080" }
python -c "import yfinance" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Missing yfinance. Install dependencies with: python -m pip install -r requirements.txt"
}
$env:PRISM_PORT = $port
Start-Process -FilePath "python" -ArgumentList (Join-Path $root "src/python/dashboard.py") -WorkingDirectory $root
Write-Host "PRISM live dashboard is ready at http://localhost:$port"
