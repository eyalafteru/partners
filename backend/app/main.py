"""
PartnerCalc OS - Main Application
נקודת הכניסה הראשית של ה-API
"""
import sys
import asyncio

# Fix for Windows - psycopg async requires SelectorEventLoop
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings
from app.database import init_db, close_db

# Import API routers
from app.api import calculators, leads, scans, communication, prompts, stats, webhooks, templates, ai_reply, emails, tracking, outreach, blacklist, notifications, facebook_marketing, post_strategies, eyal_story
from app.api.admin import database as admin_database, api_keys, auto_reply as admin_auto_reply, scenarios as admin_scenarios, business_classifier as admin_classifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle management - הפעלה וסגירה של האפליקציה
    """
    # Startup
    logger.info("🚀 PartnerCalc OS מתחיל...")
    if settings.use_sqlite:
        logger.info("📊 משתמש ב-SQLite מקומי לפיתוח")
    else:
        logger.info(f"📊 מתחבר ל-Database: {settings.db_host}:{settings.db_port}")
    logger.info(f"🤖 Ollama Host: {settings.ollama_host}")
    
    # יצירת טבלאות (רק בפיתוח)
    if settings.debug:
        await init_db()
        logger.info("✅ טבלאות נוצרו/אומתו")
    
    # Start watchdog task - DISABLED temporarily to prevent DB locks
    watchdog_task = None
    # from app.tasks.watchdog_tasks import start_watchdog
    # watchdog_task = asyncio.create_task(start_watchdog())
    logger.info("🐕 Watchdog DISABLED - preventing DB locks")
    
    # Start email sync task
    email_sync_task = None
    try:
        from app.tasks.email_sync_task import start_email_sync
        email_sync_task = asyncio.create_task(start_email_sync())
        logger.info("📬 Email Sync started - listening for incoming emails")
    except Exception as e:
        logger.warning(f"📬 Email Sync failed to start: {e}")
    
    # Start email scheduler task
    email_scheduler_task = None
    try:
        from app.tasks.email_scheduler import start_email_scheduler
        email_scheduler_task = asyncio.create_task(start_email_scheduler())
        logger.info("📧 Email Scheduler started - sending queued emails")
    except Exception as e:
        logger.warning(f"📧 Email Scheduler failed to start: {e}")
    
    # Resume incomplete pipelines on startup
    try:
        from app.services.pipeline_service import resume_incomplete_pipelines
        asyncio.create_task(resume_incomplete_pipelines())
        logger.info("🔄 Pipeline resume task started")
    except Exception as e:
        logger.warning(f"🔄 Pipeline resume failed to start: {e}")
    
    # Start Facebook Marketing tasks
    facebook_task = None
    try:
        from app.tasks.facebook_tasks import start_facebook_tasks
        facebook_task = asyncio.create_task(start_facebook_tasks())
        logger.info("📘 Facebook Marketing tasks started")
    except Exception as e:
        logger.warning(f"📘 Facebook Marketing tasks failed to start: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 PartnerCalc OS נסגר...")
    if watchdog_task:
        watchdog_task.cancel()
    if email_sync_task:
        email_sync_task.cancel()
    if email_scheduler_task:
        email_scheduler_task.cancel()
    if facebook_task:
        facebook_task.cancel()
    await close_db()


# יצירת האפליקציה
app = FastAPI(
    title="PartnerCalc OS",
    description="מערכת שותפויות מחשבונים - API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Middleware for Chrome Extension (must be added BEFORE CORSMiddleware)
class ChromeExtensionCORSMiddleware(BaseHTTPMiddleware):
    """Allow CORS from any chrome-extension:// origin"""
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "")
        if origin.startswith("chrome-extension://"):
            if request.method == "OPTIONS":
                return Response(status_code=200, headers={
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Credentials": "true",
                })
            response = await call_next(request)
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        return await call_next(request)

# CORS - אפשר גישה מה-Frontend (added FIRST = innermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:3001",  # Next.js dev (alternate port)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chrome Extension CORS (added LAST = outermost = runs FIRST)
# This intercepts chrome-extension:// origins before CORSMiddleware rejects them
app.add_middleware(ChromeExtensionCORSMiddleware)

# Static files - קבצי וידאו וכו'
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
(static_dir / "videos").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ========== API Routes ==========

# מחשבונים
app.include_router(
    calculators.router,
    prefix="/api/calculators",
    tags=["מחשבונים"]
)

# לידים
app.include_router(
    leads.router,
    prefix="/api/leads",
    tags=["לידים"]
)

# סריקות
app.include_router(
    scans.router,
    prefix="/api/scans",
    tags=["סריקות"]
)

# תקשורת
app.include_router(
    communication.router,
    prefix="/api/communication",
    tags=["תקשורת"]
)

# פרומפטים
app.include_router(
    prompts.router,
    prefix="/api/prompts",
    tags=["פרומפטים"]
)

# סטטיסטיקות
app.include_router(
    stats.router,
    prefix="/api/stats",
    tags=["סטטיסטיקות"]
)

# Webhooks
app.include_router(
    webhooks.router,
    prefix="/api/webhooks",
    tags=["Webhooks"]
)

# תבניות מייל
app.include_router(
    templates.router,
    prefix="/api/templates",
    tags=["תבניות מייל"]
)

# AI Reply - תשובות AI
app.include_router(
    ai_reply.router,
    prefix="/api/ai-reply",
    tags=["AI Reply"]
)

# Emails - ניהול מיילים
app.include_router(
    emails.router,
    prefix="/api/emails",
    tags=["Emails"]
)

# Tracking - מעקב פתיחות וקליקים
app.include_router(
    tracking.router,
    prefix="/api/tracking",
    tags=["Tracking"]
)

# Admin - Database Explorer
app.include_router(
    admin_database.router,
    prefix="/api/admin/database",
    tags=["Admin - Database"]
)

# Admin - API Keys
app.include_router(
    api_keys.router,
    prefix="/api/admin/api-keys",
    tags=["Admin - API Keys"]
)

# Admin - Auto Reply
app.include_router(
    admin_auto_reply.router,
    prefix="/api/admin/auto-reply",
    tags=["Admin - Auto Reply"]
)

# Admin - Scenarios (תרחישי תשובות)
app.include_router(
    admin_scenarios.router,
    prefix="/api/admin/scenarios",
    tags=["Admin - Scenarios"]
)

# Admin - Business Classifier (סיווג עסקים גלובלי)
app.include_router(
    admin_classifier.router,
    prefix="/api/admin/classifier",
    tags=["Admin - Classifier"]
)

# Outreach - ניהול שליחת מיילים
app.include_router(
    outreach.router,
    prefix="/api/outreach",
    tags=["Outreach"]
)

# Blacklist - רשימה שחורה
app.include_router(
    blacklist.router,
    prefix="/api/blacklist",
    tags=["Blacklist"]
)

# Notifications - התראות WhatsApp
app.include_router(
    notifications.router,
    tags=["Notifications"]
)

# Facebook Marketing - פרסום בקבוצות פייסבוק
app.include_router(
    facebook_marketing.router,
    prefix="/api/facebook",
    tags=["Facebook Marketing"]
)

# Post Strategies - אסטרטגיות כתיבה
app.include_router(
    post_strategies.router,
    prefix="/api/strategies",
    tags=["Post Strategies"]
)

# Eyal Story - הסיפור של אייל לשימוש ב-AI
app.include_router(
    eyal_story.router,
    prefix="/api/eyal-story",
    tags=["Eyal Story"]
)


# ========== Health Check ==========

@app.get("/", tags=["Health"])
async def root():
    """בדיקת תקינות בסיסית"""
    return {
        "status": "online",
        "app": "PartnerCalc OS",
        "version": "1.0.0"
    }


@app.get("/api/health", tags=["Health"])
async def health_check():
    """בדיקת תקינות מורחבת"""
    return {
        "status": "healthy",
        "database": settings.db_host,
        "ollama": settings.ollama_host,
        "environment": settings.app_env
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
