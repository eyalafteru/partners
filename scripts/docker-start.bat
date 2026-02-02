@echo off
chcp 65001 > nul
echo ========================================
echo    🐳 PartnerCalc OS - Docker Mode
echo ========================================
echo.

:: Navigate to docker folder
cd /d "%~dp0\..\docker"

:: Check Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [X] Docker לא פעיל!
    echo     אנא הפעל את Docker Desktop ונסה שוב.
    echo.
    pause
    exit /b 1
)

echo ✅ Docker פעיל
echo.

:: Stop existing containers
echo 🛑 עוצר containers קיימים...
docker-compose down 2>nul
echo.

:: Build and start
echo 🔨 בונה ומפעיל containers...
echo    (זה יכול לקחת כמה דקות בפעם הראשונה)
echo.
docker-compose up -d --build

if %ERRORLEVEL% neq 0 (
    echo.
    echo [X] שגיאה בהפעלת Docker!
    echo     בדוק את הלוגים עם: docker-compose logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ המערכת פועלת ב-Docker!
echo ========================================
echo.
echo    Frontend: http://localhost:3000
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo    לצפייה בלוגים: docker-compose logs -f
echo    לעצירה:        docker-compose down
echo.
echo ========================================

:: Wait for services to be ready
echo ⏳ ממתין לשרתים...
timeout /t 10 /nobreak > nul

:: Open browser
echo 🌐 פותח דפדפן...
start http://localhost:3000

echo.
echo לחץ על מקש כלשהו לסגירה (המערכת תמשיך לרוץ ברקע)
pause > nul
