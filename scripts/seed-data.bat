@echo off
chcp 65001 >nul
echo ================================================
echo    PartnerCalc OS - Seed Initial Data
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

:: Run seed script
echo [1/2] Seeding default prompts...
python -c "
from app.database import SessionLocal
from app.data.default_prompts import DEFAULT_PROMPTS
from app.models.prompt import Prompt

db = SessionLocal()
try:
    for p in DEFAULT_PROMPTS:
        existing = db.query(Prompt).filter(Prompt.node_name == p['node_name']).first()
        if not existing:
            prompt = Prompt(**p)
            db.add(prompt)
            print(f'  Added: {p[\"node_name\"]}')
        else:
            print(f'  Exists: {p[\"node_name\"]}')
    db.commit()
    print('Done!')
except Exception as e:
    print(f'Error: {e}')
finally:
    db.close()
"

echo.
echo [2/2] Seeding default API keys (templates)...
python -c "
from app.database import SessionLocal
from app.models.api_key import ApiKey

db = SessionLocal()
services = [
    ('whatsapp', 'WhatsApp (Green-API)'),
    ('sendgrid', 'Email (SendGrid)'),
    ('twilio', 'SMS (Twilio)'),
    ('apify', 'Apify (Scraper)'),
    ('ollama', 'Ollama (Local AI)')
]
try:
    for name, display in services:
        existing = db.query(ApiKey).filter(ApiKey.service_name == name).first()
        if not existing:
            key = ApiKey(service_name=name, display_name=display, is_active=False)
            db.add(key)
            print(f'  Added: {name}')
        else:
            print(f'  Exists: {name}')
    db.commit()
    print('Done!')
except Exception as e:
    print(f'Error: {e}')
finally:
    db.close()
"

echo.
echo ================================================
echo   Data seeding complete!
echo ================================================
pause
