# Restart Backend Server Script
# Run with: powershell -ExecutionPolicy Bypass -File restart-backend.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🔄 מפעיל מחדש את השרת Backend" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kill processes on port 8001
Write-Host "🛑 סוגר תהליכים על פורט 8001..." -ForegroundColor Yellow
$connections = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue
foreach ($conn in $connections) {
    $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "   סוגר: $($process.ProcessName) (PID: $($process.Id))" -ForegroundColor Red
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}

# Kill any python/uvicorn processes
Write-Host "🛑 סוגר תהליכי Python/Uvicorn..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -match "python|uvicorn" } | ForEach-Object {
    Write-Host "   סוגר: $($_.ProcessName) (PID: $($_.Id))" -ForegroundColor Red
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "⏳ ממתין 3 שניות..." -ForegroundColor Gray
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "🚀 מפעיל את השרת..." -ForegroundColor Green

# Change to backend directory
Set-Location "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\backend"

# Activate venv and start server
& .\venv\Scripts\Activate.ps1
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\backend'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --host 0.0.0.0 --port 8001"

Write-Host ""
Write-Host "✅ השרת הופעל בחלון חדש!" -ForegroundColor Green
Write-Host "   כתובת: http://localhost:8001" -ForegroundColor White
Write-Host "   API Docs: http://localhost:8001/docs" -ForegroundColor White
Write-Host ""
Write-Host "לחץ Enter לסגירה..." -ForegroundColor Gray
Read-Host
