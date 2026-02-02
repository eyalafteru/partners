"""
PartnerCalc OS - Celery Configuration
הגדרות Celery לביצוע משימות רקע
"""
from celery import Celery

from app.config import settings

# יצירת Celery app
celery_app = Celery(
    "partnercalc",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.scan_tasks",
        "app.tasks.outreach_tasks",
        "app.tasks.watchdog_tasks",
    ]
)

# הגדרות
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Jerusalem",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 שעה מקסימום למשימה
    worker_prefetch_multiplier=1,  # משימה אחת בכל פעם
    
    # Retry settings
    task_default_retry_delay=60,  # דקה בין ניסיונות
    task_max_retries=3,
)

# Beat schedule (משימות מתוזמנות)
celery_app.conf.beat_schedule = {
    # בדיקת התקנות כל 24 שעות
    "verify-installations-daily": {
        "task": "app.tasks.watchdog_tasks.verify_all_installations",
        "schedule": 86400.0,  # 24 שעות
    },
    # ניקוי לוגים ישנים כל שבוע
    "cleanup-old-logs-weekly": {
        "task": "app.tasks.watchdog_tasks.cleanup_old_logs",
        "schedule": 604800.0,  # 7 ימים
    },
}
