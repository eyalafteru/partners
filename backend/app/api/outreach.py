"""
PartnerCalc OS - Outreach API
ניהול תור מיילים ושליחה מתוזמנת
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from loguru import logger

from app.database import get_async_session
from app.models import Lead, EmailQueue, Blacklist, EmailTemplate

router = APIRouter()


# ========== Schemas ==========

class QueueEmailRequest(BaseModel):
    """בקשה להוספת לידים לתור"""
    lead_ids: List[int]
    template_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None


class OutreachSettings(BaseModel):
    """הגדרות Outreach"""
    daily_limit: int = 100
    start_hour: int = 8
    end_hour: int = 20
    interval_minutes: int = 15
    enabled: bool = True


# ========== Helper Functions ==========

async def get_settings(session: AsyncSession) -> dict:
    """קבלת הגדרות Outreach"""
    from sqlalchemy import text
    result = await session.execute(text("SELECT key, value FROM outreach_settings"))
    rows = result.fetchall()
    settings = {}
    for key, value in rows:
        if key in ['daily_limit', 'start_hour', 'end_hour', 'interval_minutes']:
            settings[key] = int(value)
        elif key == 'enabled':
            settings[key] = value.lower() == 'true'
        else:
            settings[key] = value
    return settings


async def is_blacklisted(session: AsyncSession, email: str, domain: str = None) -> bool:
    """בדיקה אם מייל/דומיין ברשימה שחורה"""
    conditions = [Blacklist.email == email]
    if domain:
        conditions.append(Blacklist.domain == domain)
    
    result = await session.execute(
        select(Blacklist).where(or_(*conditions)).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def can_contact_lead(lead: Lead) -> tuple[bool, str]:
    """
    בדיקה האם ניתן לפנות לליד
    מחזיר: (can_contact, reason)
    """
    # No email
    if not lead.email:
        return False, "no_email"
    
    # Already contacted but no response - BLOCKED
    if lead.last_contacted_at and not lead.last_response_at:
        return False, "contacted_no_response"
    
    # Blacklisted status
    if lead.status == "blacklisted":
        return False, "blacklisted"
    
    # Bounced status
    if lead.status == "bounced":
        return False, "bounced"
    
    return True, "ok"


# ========== Test Send Endpoint ==========

class TestSendRequest(BaseModel):
    """בקשה לשליחת טסט"""
    lead_id: int
    template_id: Optional[int] = None
    subject: Optional[str] = None
    body: Optional[str] = None


# 🧪 Test emails - allowed to receive unlimited emails
TEST_EMAILS = [
    "afterunew@gmail.com",
    "eyal@afteru.co.il",
    "test@test.com"
]


@router.post("/test-send")
async def test_send_to_lead(
    request: TestSendRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת מייל טסט מיידית לליד בודד
    לא עובר דרך התור - נשלח מיד!
    """
    from app.services.smtp_service import get_smtp_service
    from app.models.communication import Communication
    
    # Get lead
    result = await session.execute(
        select(Lead).where(Lead.id == request.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # Get email
    email = None
    if lead.contact_info:
        email = lead.contact_info.get('whois_email') or (lead.contact_info.get('emails') or [None])[0]
    
    if not email:
        raise HTTPException(status_code=400, detail="אין מייל לליד")
    
    # 🧪 Check if test email - skip blocking rules
    is_test_email = email.lower() in [e.lower() for e in TEST_EMAILS]
    
    # Check if can contact (skip for test emails)
    if not is_test_email:
        if lead.last_contacted_at and not lead.last_response_at:
            raise HTTPException(status_code=400, detail="כבר נשלח מייל לליד זה וטרם התקבלה תשובה")
    
    # Get template
    template = None
    if request.template_id:
        result = await session.execute(
            select(EmailTemplate).where(EmailTemplate.id == request.template_id)
        )
        template = result.scalar_one_or_none()
    
    # Get campaign for keywords (category)
    campaign = None
    from app.models import ScanCampaign, ScanQueue
    
    # First try source_campaign_id
    if hasattr(lead, 'source_campaign_id') and lead.source_campaign_id:
        camp_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == lead.source_campaign_id)
        )
        campaign = camp_result.scalar_one_or_none()
    
    # Fallback: look up campaign via scan_queue by domain
    if not campaign and lead.domain:
        camp_result = await session.execute(
            select(ScanCampaign)
            .join(ScanQueue, ScanQueue.campaign_id == ScanCampaign.id)
            .where(ScanQueue.domain == lead.domain)
            .limit(1)
        )
        campaign = camp_result.scalar_one_or_none()
    
    # Use template engine for proper variable replacement
    from app.services.template_engine import render_template, prepare_email_variables
    
    # Build subject and body from template or request
    raw_subject = request.subject or (template.subject if template else "הצעה לשיתוף פעולה")
    raw_body = request.body or (template.body_text if template else "שלום, אני מעוניין לשתף פעולה.")
    
    # Get calculator if exists
    calculator = None
    if lead.recommended_calc_id:
        from app.models import Calculator
        calc_result = await session.execute(
            select(Calculator).where(Calculator.id == lead.recommended_calc_id)
        )
        calculator = calc_result.scalar_one_or_none()
    
    # Prepare all variables using the template engine
    variables = prepare_email_variables(
        lead=lead,
        calculator=calculator,
        campaign=campaign
    )
    
    # Render the template with all variables
    subject = render_template(raw_subject, variables)
    body = render_template(raw_body, variables)
    
    # Create communication record
    comm = Communication(
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        subject=subject,
        message_body=body
    )
    session.add(comm)
    await session.flush()
    
    # Send email
    smtp = get_smtp_service()
    result = await smtp.send_email_async(
        to_email=email,
        subject=subject,
        body=body,
        communication_id=comm.id,
        enable_tracking=False  # Disabled - trycloudflare.com is blacklisted by Spamhaus
    )
    
    if result["success"]:
        comm.status = "sent"
        comm.sent_at = datetime.utcnow()
        comm.external_id = result.get("message_id")
        
        # Update lead
        lead.last_contacted_at = datetime.utcnow()
        lead.outreach_count = (lead.outreach_count or 0) + 1
        if lead.status == "matched":
            lead.status = "contacted"
        
        await session.commit()
        
        logger.info(f"✅ Test email sent to {email} for lead {lead.domain}")
        return {
            "success": True,
            "message": f"מייל נשלח ל-{email}",
            "email": email,
            "domain": lead.domain
        }
    else:
        comm.status = "failed"
        existing_metadata = comm.metadata if isinstance(comm.metadata, dict) else {}
        comm.metadata = {**existing_metadata, "error": result.get("error")}
        await session.commit()
        
        raise HTTPException(status_code=500, detail=f"שליחה נכשלה: {result.get('error')}")


# ========== Queue Endpoints ==========

@router.post("/queue")
async def add_to_queue(
    request: QueueEmailRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    הוספת לידים לתור השליחה
    
    כללים:
    - לא ניתן להוסיף ליד שכבר נפנה ולא השיב
    - לא ניתן להוסיף ליד ברשימה שחורה
    - לא ניתן להוסיף ליד שכבר בתור
    """
    added = 0
    skipped = []
    errors = []
    
    # Get template if provided
    template = None
    if request.template_id:
        result = await session.execute(
            select(EmailTemplate).where(EmailTemplate.id == request.template_id)
        )
        template = result.scalar_one_or_none()
    
    # Get settings for scheduling
    settings = await get_settings(session)
    
    # Calculate next available slot
    now = datetime.now()
    next_slot = now.replace(second=0, microsecond=0)
    
    # Count emails already scheduled for today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    result = await session.execute(
        select(func.count(EmailQueue.id)).where(
            and_(
                EmailQueue.scheduled_at >= today_start,
                EmailQueue.scheduled_at < today_end,
                EmailQueue.status == "pending"
            )
        )
    )
    today_count = result.scalar() or 0
    
    if today_count >= settings.get('daily_limit', 100):
        # Move to tomorrow
        next_slot = (today_start + timedelta(days=1)).replace(
            hour=settings.get('start_hour', 8)
        )
    
    for lead_id in request.lead_ids:
        # Get lead
        result = await session.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            errors.append({"lead_id": lead_id, "reason": "not_found"})
            continue
        
        # Check if can contact
        can_send, reason = await can_contact_lead(lead)
        if not can_send:
            skipped.append({"lead_id": lead_id, "domain": lead.domain, "reason": reason})
            continue
        
        # Check blacklist
        email = lead.email
        domain = lead.domain
        if await is_blacklisted(session, email, domain):
            skipped.append({"lead_id": lead_id, "domain": domain, "reason": "blacklisted"})
            continue
        
        # Check if already in queue
        existing = await session.execute(
            select(EmailQueue).where(
                and_(
                    EmailQueue.lead_id == lead_id,
                    EmailQueue.status == "pending"
                )
            )
        )
        if existing.scalar_one_or_none():
            skipped.append({"lead_id": lead_id, "domain": domain, "reason": "already_queued"})
            continue
        
        # Prepare email content
        subject = request.subject or (template.subject if template else f"הצעה לשיתוף פעולה - {lead.domain}")
        body = request.body or (template.body if template else "")
        
        # Replace placeholders
        if lead.site_name:
            subject = subject.replace("{{site_name}}", lead.site_name)
            body = body.replace("{{site_name}}", lead.site_name)
        if lead.domain:
            subject = subject.replace("{{domain}}", lead.domain)
            body = body.replace("{{domain}}", lead.domain)
        
        # Create queue entry
        queue_item = EmailQueue(
            lead_id=lead_id,
            template_id=request.template_id,
            to_email=email,
            subject=subject,
            body=body,
            scheduled_at=next_slot,
            status="pending"
        )
        session.add(queue_item)
        
        # Update lead status to queued
        lead.status = "queued"
        
        added += 1
        
        # Move to next slot (spread throughout day)
        interval = settings.get('interval_minutes', 15)
        next_slot = next_slot + timedelta(minutes=interval)
        
        # If past end hour, move to next day
        if next_slot.hour >= settings.get('end_hour', 20):
            next_slot = (next_slot + timedelta(days=1)).replace(
                hour=settings.get('start_hour', 8),
                minute=0
            )
    
    await session.commit()
    
    return {
        "status": "success",
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "message": f"נוספו {added} לידים לתור"
    }


@router.get("/queue")
async def get_queue(
    status: Optional[str] = Query(None, description="סינון לפי סטטוס"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת תור המיילים"""
    query = select(EmailQueue).options(selectinload(EmailQueue.lead))
    
    if status:
        query = query.where(EmailQueue.status == status)
    
    query = query.order_by(EmailQueue.scheduled_at.asc())
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Count total
    count_query = select(func.count(EmailQueue.id))
    if status:
        count_query = count_query.where(EmailQueue.status == status)
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    return {
        "items": [
            {
                "id": item.id,
                "lead_id": item.lead_id,
                "lead_domain": item.lead.domain if item.lead else None,
                "to_email": item.to_email,
                "subject": item.subject,
                "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
                "sent_at": item.sent_at.isoformat() if item.sent_at else None,
                "status": item.status,
                "error_message": item.error_message,
                "retry_count": item.retry_count
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.delete("/queue/{queue_id}")
async def cancel_queue_item(
    queue_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """ביטול מייל בתור"""
    result = await session.execute(
        select(EmailQueue).where(EmailQueue.id == queue_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")
    
    if item.status != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot cancel item with status: {item.status}")
    
    item.status = "cancelled"
    
    # Update lead status back to matched if still queued
    lead_result = await session.execute(
        select(Lead).where(Lead.id == item.lead_id)
    )
    lead = lead_result.scalar_one_or_none()
    if lead and lead.status == "queued":
        lead.status = "matched"
    
    await session.commit()
    
    return {"status": "cancelled", "id": queue_id}


# ========== Settings Endpoints ==========

@router.get("/settings")
async def get_outreach_settings(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת הגדרות Outreach"""
    settings = await get_settings(session)
    return settings


@router.put("/settings")
async def update_outreach_settings(
    new_settings: OutreachSettings,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון הגדרות Outreach"""
    from sqlalchemy import text
    
    settings_dict = new_settings.dict()
    
    for key, value in settings_dict.items():
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        else:
            value = str(value)
        
        await session.execute(
            text("""
                INSERT OR REPLACE INTO outreach_settings (key, value, updated_at) 
                VALUES (:key, :value, :updated_at)
            """),
            {"key": key, "value": value, "updated_at": datetime.now()}
        )
    
    await session.commit()
    
    return {"status": "updated", "settings": settings_dict}


# ========== Stats Endpoints ==========

@router.get("/stats")
async def get_outreach_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """סטטיסטיקות Outreach"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    # Today's stats
    today_pending = await session.execute(
        select(func.count(EmailQueue.id)).where(
            and_(
                EmailQueue.scheduled_at >= today_start,
                EmailQueue.status == "pending"
            )
        )
    )
    
    today_sent = await session.execute(
        select(func.count(EmailQueue.id)).where(
            and_(
                EmailQueue.sent_at >= today_start,
                EmailQueue.status == "sent"
            )
        )
    )
    
    today_failed = await session.execute(
        select(func.count(EmailQueue.id)).where(
            and_(
                EmailQueue.scheduled_at >= today_start,
                EmailQueue.status == "failed"
            )
        )
    )
    
    # Total stats
    total_pending = await session.execute(
        select(func.count(EmailQueue.id)).where(EmailQueue.status == "pending")
    )
    
    total_sent = await session.execute(
        select(func.count(EmailQueue.id)).where(EmailQueue.status == "sent")
    )
    
    # Leads stats
    leads_can_contact = await session.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.status.in_(["matched", "responded"]),
                Lead.last_contacted_at.is_(None) | Lead.last_response_at.isnot(None)
            )
        )
    )
    
    leads_waiting_response = await session.execute(
        select(func.count(Lead.id)).where(
            and_(
                Lead.status == "contacted",
                Lead.last_response_at.is_(None)
            )
        )
    )
    
    leads_responded = await session.execute(
        select(func.count(Lead.id)).where(Lead.status == "responded")
    )
    
    # Get settings
    settings = await get_settings(session)
    
    return {
        "today": {
            "pending": today_pending.scalar() or 0,
            "sent": today_sent.scalar() or 0,
            "failed": today_failed.scalar() or 0
        },
        "total": {
            "pending": total_pending.scalar() or 0,
            "sent": total_sent.scalar() or 0
        },
        "leads": {
            "can_contact": leads_can_contact.scalar() or 0,
            "waiting_response": leads_waiting_response.scalar() or 0,
            "responded": leads_responded.scalar() or 0
        },
        "settings": settings
    }


@router.get("/contactable-leads")
async def get_contactable_leads(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת לידים שניתן לפנות אליהם
    
    לידים שעומדים בתנאים:
    - יש להם מייל
    - לא נפנו או שהשיבו
    - לא ברשימה שחורה
    - לא bounced
    """
    # Build query for contactable leads
    query = select(Lead).where(
        and_(
            # Has email (through contact_info JSON)
            Lead.contact_info.isnot(None),
            # Never contacted OR responded
            or_(
                Lead.last_contacted_at.is_(None),
                Lead.last_response_at.isnot(None)
            ),
            # Not blocked statuses
            Lead.status.notin_(["blacklisted", "bounced", "queued"])
        )
    )
    
    if category:
        query = query.where(Lead.category == category)
    
    query = query.order_by(Lead.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    leads = result.scalars().all()
    
    # Filter leads that actually have email
    contactable = [
        {
            "id": lead.id,
            "domain": lead.domain,
            "site_name": lead.site_name,
            "category": lead.category,
            "email": lead.email,
            "status": lead.status,
            "can_contact": lead.can_contact,
            "outreach_count": lead.outreach_count or 0,
            "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
            "last_response_at": lead.last_response_at.isoformat() if lead.last_response_at else None,
            "recommended_calc_id": lead.recommended_calc_id
        }
        for lead in leads
        if lead.email  # Only include leads with actual email
    ]
    
    return {
        "items": contactable,
        "total": len(contactable),
        "limit": limit,
        "offset": offset
    }
