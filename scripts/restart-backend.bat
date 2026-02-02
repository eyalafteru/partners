@echo off
chcp 65001 > nul
echo ========================================
echo    🔄 מפעיל מחדש את השרת Backend
echo ========================================
echo.

echo 🛑 סוגר תהליכים ישנים על פורט 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do (
    echo    סוגר תהליך PID: %%a
    taskkill /F /PID %%a 2>nul
)

echo 🛑 סוגר תהליכי Python/Uvicorn...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul

echo.
echo ⏳ ממתין 3 שניות...
timeout /t 3 /nobreak > nul

echo.
echo 🚀 מפעיל את השרת...
cd /d "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\backend"
call venv\Scripts\activate.bat
start "Backend Server" cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo.
echo ✅ השרת הופעל בחלון חדש!
echo    כתובת: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
pause
