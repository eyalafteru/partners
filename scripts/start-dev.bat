@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
echo ================================================
echo    PartnerCalc OS - Start Development
echo ================================================
echo.

:: Navigate to project root
cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%

:: Check Python
python --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found!
    goto :error
)

:: Check Node
node --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Node.js not found!
    goto :error
)

:: Check venv exists
if not exist "backend\venv" (
    echo [X] Backend venv not found. Run setup.bat first.
    goto :error
)

:: Start Backend
echo [1/2] Starting Backend (FastAPI)...
cd backend
start "PartnerCalc-Backend" cmd /k "call venv\Scripts\activate.bat && uvicorn app.main:app --host 0.0.0.0 --port 8000"

cd "%PROJECT_ROOT%"

:: Start Frontend
echo [2/2] Starting Frontend (Next.js)...
cd frontend
start "PartnerCalc-Frontend" cmd /k "npm run dev"

cd "%PROJECT_ROOT%"

echo.
echo ================================================
echo   Development servers starting...
echo.
echo   Backend:  http://localhost:8000
echo   API Docs: http://localhost:8000/api/docs
echo   Frontend: http://localhost:3000
echo.
echo   Close the terminal windows to stop.
echo ================================================

endlocal
goto :eof

:error
echo.
echo [X] Startup failed!
endlocal
exit /b 1
