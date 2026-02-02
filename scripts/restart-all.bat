@echo off
chcp 65001 > nul
echo ========================================
echo    🔄 הפעלה מחדש של כל המערכת
echo ========================================
echo.

echo 🛑 סוגר תהליכים ישנים...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM uvicorn.exe 2>nul
taskkill /F /IM node.exe 2>nul

echo.
echo ⏳ ממתין 3 שניות...
timeout /t 3 /nobreak > nul

echo.
echo 🚀 מפעיל Backend (פורט 8000)...
cd /d "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\backend"
start "Backend Server" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo.
echo ⏳ ממתין 3 שניות...
timeout /t 3 /nobreak > nul

echo.
echo 🚀 מפעיל Frontend (פורט 3000)...
cd /d "C:\Users\eyal\מערכת שיתופי פעולה\partnercalc-os\frontend"
start "Frontend Server" cmd /k "npm run dev"

echo.
echo ========================================
echo ✅ המערכת הופעלה!
echo ========================================
echo.
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:8000/docs
echo.
echo ⏳ ממתין 5 שניות ופותח את הדפדפן...
timeout /t 5 /nobreak > nul
start http://localhost:3000/scans
