"""Auto-Reply Settings API Routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ...database import get_db
from ...models.auto_reply import AutoReply

router = APIRouter(tags=["Admin - Auto Reply"])

# Default settings
DEFAULT_SETTINGS = {
    "whatsapp_enabled": True,
    "whatsapp_mode": "suggest",
    "whatsapp_delay_seconds": 30,
    "email_enabled": True,
    "email_mode": "suggest",
    "email_delay_seconds": 60,
    "sms_enabled": False,
    "sms_mode": "off",
    "sms_delay_seconds": 60,
    "business_hours_only": True,
    "business_hours_start": "09:00",
    "business_hours_end": "18:00",
    "max_auto_replies_per_lead": 3,
    "keywords_trigger_human": ["אנושי", "נציג", "טלפון", "דחוף"]
}


@router.get("/settings")
async def get_settings(db: Session = Depends(get_db)):
    """Get auto-reply settings."""
    settings = db.query(AutoReply).first()
    
    if not settings:
        return DEFAULT_SETTINGS
    
    return {
        "whatsapp_enabled": settings.whatsapp_enabled,
        "whatsapp_mode": settings.whatsapp_mode,
        "whatsapp_delay_seconds": settings.whatsapp_delay_seconds,
        "email_enabled": settings.email_enabled,
        "email_mode": settings.email_mode,
        "email_delay_seconds": settings.email_delay_seconds,
        "sms_enabled": settings.sms_enabled,
        "sms_mode": settings.sms_mode,
        "sms_delay_seconds": settings.sms_delay_seconds,
        "business_hours_only": settings.business_hours_only,
        "business_hours_start": settings.business_hours_start,
        "business_hours_end": settings.business_hours_end,
        "max_auto_replies_per_lead": settings.max_auto_replies_per_lead,
        "keywords_trigger_human": settings.keywords_trigger_human or []
    }


@router.put("/settings")
async def update_settings(data: dict, db: Session = Depends(get_db)):
    """Update auto-reply settings."""
    settings = db.query(AutoReply).first()
    
    if not settings:
        settings = AutoReply(
            whatsapp_enabled=data.get("whatsapp_enabled", True),
            whatsapp_mode=data.get("whatsapp_mode", "suggest"),
            whatsapp_delay_seconds=data.get("whatsapp_delay_seconds", 30),
            email_enabled=data.get("email_enabled", True),
            email_mode=data.get("email_mode", "suggest"),
            email_delay_seconds=data.get("email_delay_seconds", 60),
            sms_enabled=data.get("sms_enabled", False),
            sms_mode=data.get("sms_mode", "off"),
            sms_delay_seconds=data.get("sms_delay_seconds", 60),
            business_hours_only=data.get("business_hours_only", True),
            business_hours_start=data.get("business_hours_start", "09:00"),
            business_hours_end=data.get("business_hours_end", "18:00"),
            max_auto_replies_per_lead=data.get("max_auto_replies_per_lead", 3),
            keywords_trigger_human=data.get("keywords_trigger_human", [])
        )
        db.add(settings)
    else:
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
    
    db.commit()
    return {"status": "saved"}
