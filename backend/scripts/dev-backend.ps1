# Uruchom backend na wolnym porcie (domyślnie 8000).
# Zatrzymuje wiszące procesy uvicorn/python na tym porcie.

param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Szukam procesów na porcie $Port..."
$connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
if ($connections) {
    $pids = $connections.OwningProcess | Sort-Object -Unique
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "Zatrzymuję PID $procId ($($proc.ProcessName))..."
            Stop-Process -Id $procId -Force
        }
    }
} else {
    Write-Host "Port $Port jest wolny."
}

Set-Location $backendRoot
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Error "Brak .venv w $backendRoot – uruchom: python -m venv .venv && pip install -r requirements.txt"
}

Write-Host "Start uvicorn na porcie $Port..."
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port $Port
