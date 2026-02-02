@echo off
chcp 65001 > nul
echo ========================================
echo    🛑 PartnerCalc OS - Docker Stop
echo ========================================
echo.

cd /d "%~dp0\..\docker"

echo עוצר את כל ה-containers...
docker-compose down

echo.
echo ✅ המערכת נעצרה.
echo.
pause
