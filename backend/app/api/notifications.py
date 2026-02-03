"""
PartnerCalc OS - Notifications API
ניהול התראות WhatsApp
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.notifications import NotificationPhone, NotificationLog

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ========== Schemas ==========

class PhoneCreate(BaseModel):
    phone: str
    name: Optional[str] = None

class PhoneResponse(BaseModel):
    id: int
    phone: str
    name: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class LogResponse(BaseModel):
    id: int
    phone: str
    message: str
    status: str
    error: Optional[str]
    related_email_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Phone Numbers ==========

@router.get("/phones", response_model=List[PhoneResponse])
def get_phones(db: Session = Depends(get_db)):
    """קבלת כל מספרי הטלפון להתראות"""
    phones = db.execute(
        select(NotificationPhone).order_by(NotificationPhone.created_at)
    ).scalars().all()
    return phones


@router.post("/phones", response_model=PhoneResponse)
def add_phone(data: PhoneCreate, db: Session = Depends(get_db)):
    """הוספת מספר טלפון להתראות"""
    # נרמול המספר
    phone = data.phone.replace("-", "").replace(" ", "").replace("+", "")
    if phone.startswith("0"):
        phone = "972" + phone[1:]
    
    # בדיקה אם קיים
    existing = db.execute(
        select(NotificationPhone).where(NotificationPhone.phone == phone)
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already exists")
    
    new_phone = NotificationPhone(
        phone=phone,
        name=data.name,
        is_active=True
    )
    db.add(new_phone)
    db.commit()
    db.refresh(new_phone)
    return new_phone


@router.delete("/phones/{phone_id}")
def delete_phone(phone_id: int, db: Session = Depends(get_db)):
    """מחיקת מספר טלפון"""
    phone = db.get(NotificationPhone, phone_id)
    if not phone:
        raise HTTPException(status_code=404, detail="Phone not found")
    
    db.delete(phone)
    db.commit()
    return {"message": "Phone deleted"}


@router.patch("/phones/{phone_id}/toggle")
def toggle_phone(phone_id: int, db: Session = Depends(get_db)):
    """הפעלה/כיבוי של מספר"""
    phone = db.get(NotificationPhone, phone_id)
    if not phone:
        raise HTTPException(status_code=404, detail="Phone not found")
    
    phone.is_active = not phone.is_active
    db.commit()
    return {"is_active": phone.is_active}


# ========== Logs ==========

@router.get("/logs", response_model=List[LogResponse])
def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    """קבלת לוג התראות"""
    logs = db.execute(
        select(NotificationLog)
        .order_by(desc(NotificationLog.created_at))
        .limit(limit)
    ).scalars().all()
    return logs


@router.post("/test")
async def test_notification(db: Session = Depends(get_db)):
    """שליחת הודעת טסט לכל המספרים הפעילים"""
    from app.services.whatsapp_service import get_whatsapp_service
    
    phones = db.execute(
        select(NotificationPhone).where(NotificationPhone.is_active == True)
    ).scalars().all()
    
    if not phones:
        raise HTTPException(status_code=400, detail="No active phone numbers")
    
    wa = get_whatsapp_service()
    results = []
    
    for phone in phones:
        success = await wa.send_to_phone(
            phone.phone,
            "🧪 בדיקת התראות PartnerCalc\n\nההתראות פועלות!"
        )
        
        # שמירת לוג
        log = NotificationLog(
            phone=phone.phone,
            message="Test notification",
            status="sent" if success else "failed"
        )
        db.add(log)
        
        results.append({
            "phone": phone.phone,
            "name": phone.name,
            "success": success
        })
    
    db.commit()
    return {"results": results}
