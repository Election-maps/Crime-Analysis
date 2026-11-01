$pythonPath = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
if (-not (Test-Path $pythonPath)) {
    $pythonPath = "python"
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  POLICE CRIME ANALYSIS & INVESTIGATION REVIEW SYSTEM  " -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Launching server at http://localhost:8000 ..." -ForegroundColor Green

Start-Process "http://localhost:8000"
& $pythonPath run_server.py
