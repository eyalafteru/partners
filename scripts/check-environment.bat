@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>nul
echo ================================================
echo    PartnerCalc OS - Environment Check
echo ================================================
echo.

set ERRORS=0

:: Python
echo [1/6] Checking Python...
python --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [X] Python not found!
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo   [OK] %%i
)

:: Node.js
echo.
echo [2/6] Checking Node.js...
node --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [X] Node.js not found!
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('node --version') do echo   [OK] Node.js %%i
)

:: npm
echo.
echo [3/6] Checking npm...
npm --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [X] npm not found!
    set /a ERRORS+=1
) else (
    for /f "tokens=*" %%i in ('npm --version') do echo   [OK] npm %%i
)

:: Ollama
echo.
echo [4/6] Checking Ollama...
ollama --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [!] Ollama not installed - optional for AI features
) else (
    for /f "tokens=*" %%i in ('ollama --version 2^>^&1') do echo   [OK] %%i
)

:: Docker (optional)
echo.
echo [5/6] Checking Docker...
docker --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [!] Docker not installed - optional for Celery workers
) else (
    for /f "tokens=*" %%i in ('docker --version') do echo   [OK] %%i
)

:: Database Connection
echo.
echo [6/6] Checking Database connection...
python -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('185.151.198.29', 35432)); s.close(); print('  [OK] PostgreSQL port reachable')" 2>nul
if %ERRORLEVEL% neq 0 (
    echo   [!] Cannot reach PostgreSQL server - check network
)

:: Summary
echo.
echo ================================================
if %ERRORS% equ 0 (
    echo   All required checks passed!
) else (
    echo   %ERRORS% error(s) found. Please fix before continuing.
)
echo ================================================
echo.
endlocal
