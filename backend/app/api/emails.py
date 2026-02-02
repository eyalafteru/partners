"""
PartnerCalc OS - Emails API
ניהול מיילים נכנסים ויוצאים
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from app.database import get_async_session
from app.models.communication import Communication
from app.models.lead import Lead
from app.services.imap_service import get_imap_service
from app.services.smtp_service import get_smtp_service

router = APIRouter()


# ========== Pydantic Schemas ==========

class EmailMessage(BaseModel):
    """מייל"""
    uid: Optional[str] = None
    message_id: Optional[str] = None
    from_email: str
    from_name: Optional[str] = None
    to: Optional[str] = None
    subject: str
    text_body: Optional[str] = None
    html_body: Optional[str] = None
    received_at: Optional[datetime] = None
    has_attachments: bool = False
    attachments: List[Dict] = []
    # קשר ל-lead
    lead_id: Optional[int] = None
    lead_domain: Optional[str] = None


class SendEmailRequest(BaseModel):
    """בקשה לשליחת מייל"""
    to_email: EmailStr
    subject: str
    body: str
    html_body: Optional[str] = None
    reply_to: Optional[str] = None
    lead_id: Optional[int] = None


class EmailStats(BaseModel):
    """סטטיסטיקות מיילים"""
    total_inbox: int
    unread: int
    sent_today: int
    sent_this_week: int


# ========== API Endpoints ==========

@router.get("/inbox", response_model=List[EmailMessage])
async def get_inbox(
    limit: int = Query(default=50, le=200),
    unread_only: bool = False,
    since_days: int = Query(default=7, le=30),
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת מיילים מהתיבה
    """
    try:
        imap = get_imap_service()
        
        if unread_only:
            emails = await imap.fetch_unread_emails_async(limit=limit)
        else:
            since_date = datetime.utcnow() - timedelta(days=since_days)
            emails = await imap.fetch_new_emails_async(
                since_date=since_date,
                limit=limit
            )
        
        # העשרת המיילים עם מידע על לידים
        result = []
        for email_data in emails:
            email_msg = EmailMessage(**email_data)
            
            # חיפוש ליד לפי כתובת המייל
            from_email = email_data.get("from_email", "")
            if from_email:
                try:
                    # חיפוש בכל הלידים - בודק אם המייל מופיע ב-contact_info
                    lead_result = await session.execute(
                        select(Lead).where(
                            Lead.contact_info.isnot(None)
                        ).limit(100)
                    )
                    leads = lead_result.scalars().all()
                    
                    for lead in leads:
                        contact = lead.contact_info or {}
                        if (contact.get("whois_email") == from_email or 
                            from_email in (contact.get("emails") or [])):
                            email_msg.lead_id = lead.id
                            email_msg.lead_domain = lead.domain
                            break
                except Exception as e:
                    logger.warning(f"Failed to find lead for {from_email}: {e}")
            
            result.append(email_msg)
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to fetch inbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sent")
async def get_sent_emails(
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת מיילים שנשלחו (מה-DB)
    """
    result = await session.execute(
        select(Communication)
        .where(
            Communication.channel == "email",
            Communication.direction == "outbound"
        )
        .order_by(desc(Communication.sent_at))
        .limit(limit)
    )
    
    emails = result.scalars().all()
    
    return [
        {
            "id": e.id,
            "lead_id": e.lead_id,
            "to_email": e.recipient,
            "subject": e.subject,
            "body": e.message_body,
            "status": e.status,
            "sent_at": e.sent_at,
            "delivered_at": e.delivered_at,
            "read_at": e.read_at,
            "opens_count": e.opens_count or 0
        }
        for e in emails
    ]


@router.post("/send")
async def send_email(
    request: SendEmailRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת מייל חדש
    """
    smtp = get_smtp_service()
    
    # שליחה
    result = await smtp.send_email_async(
        to_email=request.to_email,
        subject=request.subject,
        body=request.body,
        html_body=request.html_body,
        reply_to=request.reply_to
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send"))
    
    # שמירה ב-DB רק אם יש lead_id
    communication_id = None
    if request.lead_id:
        communication = Communication(
            lead_id=request.lead_id,
            channel="email",
            direction="outbound",
            subject=request.subject,
            message_body=f"To: {request.to_email}\n\n{request.body}",
            status="sent",
            external_id=result.get("message_id"),
            sent_at=datetime.utcnow()
        )
        
        session.add(communication)
        await session.commit()
        communication_id = communication.id
    
    logger.info(f"✅ Email sent to {request.to_email}")
    
    return {
        "success": True,
        "message_id": result.get("message_id"),
        "communication_id": communication_id
    }


@router.get("/stats", response_model=EmailStats)
async def get_email_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות מיילים
    """
    try:
        # מיילים שנשלחו היום
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        
        sent_today_result = await session.execute(
            select(func.count(Communication.id))
            .where(
                Communication.channel == "email",
                Communication.direction == "outbound",
                Communication.sent_at >= today
            )
        )
        sent_today = sent_today_result.scalar() or 0
        
        sent_week_result = await session.execute(
            select(func.count(Communication.id))
            .where(
                Communication.channel == "email",
                Communication.direction == "outbound",
                Communication.sent_at >= week_ago
            )
        )
        sent_week = sent_week_result.scalar() or 0
        
        # ספירת מיילים בתיבה
        try:
            imap = get_imap_service()
            unread = await imap.fetch_unread_emails_async(limit=1)
            unread_count = len(unread) if unread else 0
            
            # קבלת מספר כולל (מהשבוע האחרון)
            all_emails = await imap.fetch_new_emails_async(
                since_date=datetime.utcnow() - timedelta(days=7),
                limit=200
            )
            total_inbox = len(all_emails) if all_emails else 0
        except:
            unread_count = 0
            total_inbox = 0
        
        return EmailStats(
            total_inbox=total_inbox,
            unread=unread_count,
            sent_today=sent_today,
            sent_this_week=sent_week
        )
    
    except Exception as e:
        logger.error(f"Failed to get email stats: {e}")
        return EmailStats(
            total_inbox=0,
            unread=0,
            sent_today=0,
            sent_this_week=0
        )


@router.get("/folders")
async def get_folders():
    """
    קבלת רשימת תיקיות בתיבה
    """
    try:
        imap = get_imap_service()
        folders = imap.get_folder_list()
        return {"folders": folders}
    except Exception as e:
        logger.error(f"Failed to get folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_inbox(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סנכרון תיבת הדואר - שליפת מיילים חדשים ושמירה ב-DB
    """
    try:
        imap = get_imap_service()
        
        # שליפת מיילים לא נקראו
        emails = await imap.fetch_unread_emails_async(limit=50)
        
        synced = 0
        for email_data in emails:
            from_email = email_data.get("from_email", "")
            
            # חיפוש ליד
            lead = None
            try:
                lead_result = await session.execute(
                    select(Lead).where(Lead.contact_info.isnot(None)).limit(100)
                )
                leads = lead_result.scalars().all()
                
                for l in leads:
                    contact = l.contact_info or {}
                    if (contact.get("whois_email") == from_email or 
                        from_email in (contact.get("emails") or [])):
                        lead = l
                        break
            except Exception as e:
                logger.warning(f"Failed to find lead for {from_email}: {e}")
            
            if lead:
                # בדיקה אם המייל כבר קיים
                existing = await session.execute(
                    select(Communication).where(
                        Communication.external_id == email_data.get("message_id")
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                # שמירת המייל
                communication = Communication(
                    lead_id=lead.id,
                    channel="email",
                    direction="inbound",
                    subject=email_data.get("subject"),
                    message_body=email_data.get("text_body"),
                    status="delivered",
                    external_id=email_data.get("message_id"),
                    sent_at=email_data.get("received_at")
                )
                
                session.add(communication)
                synced += 1
                
                # עדכון סטטוס הליד
                if lead.status == "contacted":
                    lead.status = "responded"
        
        await session.commit()
        
        logger.info(f"📬 Synced {synced} emails from inbox")
        
        return {
            "success": True,
            "synced": synced,
            "total_checked": len(emails)
        }
    
    except Exception as e:
        logger.error(f"Failed to sync inbox: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection")
async def test_email_connection():
    """
    בדיקת חיבור IMAP ו-SMTP
    """
    results = {
        "imap": False,
        "smtp": False,
        "imap_error": None,
        "smtp_error": None
    }
    
    # בדיקת IMAP
    try:
        imap = get_imap_service()
        results["imap"] = imap.verify_connection()
    except Exception as e:
        results["imap_error"] = str(e)
    
    # בדיקת SMTP
    try:
        smtp = get_smtp_service()
        results["smtp"] = smtp.verify_connection()
    except Exception as e:
        results["smtp_error"] = str(e)
    
    return results
