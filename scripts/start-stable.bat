@echo off
chcp 65001 > nul
echo ========================================
echo    🚀 PartnerCalc OS - Stable Mode
echo    (Auto-restart on crash)
echo ========================================
echo.

:: Navigate to project root
cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%

:: Check Python
python --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found!
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Node.js not found!
    pause
    exit /b 1
)

:: Check venv exists
if not exist "backend\venv" (
    echo [X] Backend venv not found. Run setup.bat first.
    pause
    exit /b 1
)

:: Kill existing processes
echo 🛑 סוגר תהליכים קיימים...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
timeout /t 2 /nobreak > nul

:: Start Frontend in separate window
echo [1/2] 🚀 מפעיל Frontend...
cd frontend
start "PartnerCalc-Frontend" cmd /k "npm run dev"
cd "%PROJECT_ROOT%"

:: Start Backend with auto-restart loop
echo [2/2] 🚀 מפעיל Backend עם restart אוטומטי...
echo.
echo ========================================
echo    Backend:  http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API Docs: http://localhost:8000/docs
echo ========================================
echo.

:: Wait for frontend to start
timeout /t 3 /nobreak > nul

:: Open browser
start http://localhost:3000

:: Backend auto-restart loop
cd backend
call venv\Scripts\activate.bat

:loop
echo.
echo [%TIME%] 🟢 מפעיל שרת Backend...
uvicorn app.main:app --host 0.0.0.0 --port 8000
echo.
echo [%TIME%] ⚠️ השרת נפל! מפעיל מחדש בעוד 5 שניות...
echo    (לחץ Ctrl+C לעצירה)
timeout /t 5 /nobreak > nul
goto loop
