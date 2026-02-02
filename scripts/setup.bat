@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
echo ================================================
echo    PartnerCalc OS - Initial Setup
echo ================================================
echo.

:: Navigate to project root
cd /d "%~dp0\.."
set PROJECT_ROOT=%CD%
echo Project root: %PROJECT_ROOT%
echo.

:: Setup Backend
echo [1/4] Setting up Backend...
cd backend

if not exist "venv" (
    echo   Creating Python virtual environment...
    python -m venv venv
    if %ERRORLEVEL% neq 0 (
        echo   [X] Failed to create venv
        goto :error
    )
)

echo   Activating venv...
call venv\Scripts\activate.bat

echo   Installing Python dependencies...
pip install -q -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo   [X] Failed to install Python dependencies
    goto :error
)
echo   [OK] Backend dependencies installed

cd "%PROJECT_ROOT%"

:: Setup Frontend
echo.
echo [2/4] Setting up Frontend...
cd frontend

if not exist "node_modules" (
    echo   Installing npm packages (this may take a few minutes)...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo   [X] Failed to install npm packages
        goto :error
    )
) else (
    echo   [OK] npm packages already installed
)

cd "%PROJECT_ROOT%"

:: Run Migrations
echo.
echo [3/4] Database setup...
cd backend
call venv\Scripts\activate.bat
echo   Running Alembic migrations...
alembic upgrade head 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [!] Migrations skipped - run manually if needed
) else (
    echo   [OK] Migrations complete
)

cd "%PROJECT_ROOT%"

:: Done
echo.
echo [4/4] Setup complete!
echo.
echo ================================================
echo   PartnerCalc OS is ready!
echo.
echo   To start development:
echo     scripts\start-dev.bat
echo.
echo   URLs:
echo     Frontend: http://localhost:3000
echo     Backend:  http://localhost:8000
echo     API Docs: http://localhost:8000/api/docs
echo ================================================

endlocal
goto :eof

:error
echo.
echo [X] Setup failed!
endlocal
exit /b 1
