@echo off
chcp 65001 >nul
echo ================================================
echo    PartnerCalc OS - Run Database Migrations
echo ================================================
echo.

cd /d %~dp0\..\backend

:: Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [!] Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

echo Running Alembic migrations...
alembic upgrade head

if %ERRORLEVEL% equ 0 (
    echo.
    echo [✓] Migrations completed successfully!
) else (
    echo.
    echo [X] Migration failed!
)

pause
