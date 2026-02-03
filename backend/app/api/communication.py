"""
PartnerCalc OS - Communication API
ניהול תקשורת - WhatsApp, Email, SMS
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from loguru import logger

from app.database import get_async_session
from app.models.communication import Communication
from app.models.lead import Lead
from app.services.smtp_service import get_smtp_service

router = APIRouter()


# ========== Pydantic Schemas ==========

class MessageCreate(BaseModel):
    """סכמה ליצירת הודעה"""
    lead_id: int
    channel: str  # whatsapp, email, sms
    message_body: str
    subject: Optional[str] = None  # למייל בלבד
    template_id: Optional[int] = None  # תבנית מייל
    html_body: Optional[str] = None  # גוף HTML


class BulkEmailCreate(BaseModel):
    """סכמה לשליחת מייל לרשימת לידים"""
    lead_ids: List[int]
    subject: str
    message_body: str
    html_body: Optional[str] = None
    template_id: Optional[int] = None


class MessageResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    lead_id: int
    channel: str
    direction: str
    message_body: str
    subject: Optional[str]
    status: str
    is_auto_reply: bool
    sent_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """סכמה לשיחה עם ליד"""
    lead_id: int
    domain: str
    site_name: Optional[str]
    messages: List[MessageResponse]
    total_messages: int


# ========== API Endpoints ==========

@router.get("/")
async def list_messages(
    skip: int = 0,
    limit: int = 100,
    lead_id: Optional[int] = None,
    channel: Optional[str] = None,
    direction: Optional[str] = None,
    group_by_recipient: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת הודעות (עם אפשרות קיבוץ לפי נמען)
    """
    query = select(Communication, Lead).join(Lead, Communication.lead_id == Lead.id, isouter=True)
    
    filters = []
    if lead_id:
        filters.append(Communication.lead_id == lead_id)
    if channel:
        filters.append(Communication.channel == channel)
    if direction:
        filters.append(Communication.direction == direction)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(Communication.sent_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    rows = result.all()
    
    # בניית רשימה עם מידע על הנמען
    messages = []
    for comm, lead in rows:
        to_email = None
        if lead and lead.contact_info:
            to_email = lead.contact_info.get("whois_email")
            if not to_email:
                emails = lead.contact_info.get("emails", [])
                if emails:
                    to_email = emails[0]
        
        messages.append({
            "id": comm.id,
            "lead_id": comm.lead_id,
            "channel": comm.channel,
            "direction": comm.direction,
            "message_body": comm.message_body,
            "subject": comm.subject,
            "status": comm.status,
            "is_auto_reply": comm.is_auto_reply,
            "sent_at": comm.sent_at,
            "opens_count": comm.opens_count,
            "clicks": comm.clicks,
            "thread_id": comm.thread_id,
            "to_email": to_email,
            "domain": lead.domain if lead else None
        })
    
    # קיבוץ לפי נמען אם מבוקש
    if group_by_recipient:
        grouped = {}
        for msg in messages:
            email = msg.get("to_email") or "unknown"
            if email not in grouped:
                grouped[email] = {
                    "email": email,
                    "messages": [],
                    "domains": set(),
                    "total_sent": 0,
                    "last_sent": None
                }
            grouped[email]["messages"].append(msg)
            grouped[email]["total_sent"] += 1
            if msg.get("domain"):
                grouped[email]["domains"].add(msg["domain"])
            if not grouped[email]["last_sent"] or (msg.get("sent_at") and msg["sent_at"] > grouped[email]["last_sent"]):
                grouped[email]["last_sent"] = msg.get("sent_at")
        
        # המרה לרשימה
        result_list = []
        for email, data in grouped.items():
            data["domains"] = list(data["domains"])
            result_list.append(data)
        
        # מיון לפי תאריך אחרון
        result_list.sort(key=lambda x: x["last_sent"] or "", reverse=True)
        return result_list
    
    return messages


@router.get("/stats")
async def message_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות הודעות
    """
    # לפי ערוץ
    result = await session.execute(
        select(Communication.channel, func.count(Communication.id))
        .where(Communication.direction == "outbound")
        .group_by(Communication.channel)
    )
    by_channel = {row[0]: row[1] for row in result.all()}
    
    # לפי סטטוס
    result = await session.execute(
        select(Communication.status, func.count(Communication.id))
        .group_by(Communication.status)
    )
    by_status = {row[0]: row[1] for row in result.all()}
    
    # תגובות שהתקבלו
    result = await session.execute(
        select(func.count(Communication.id))
        .where(Communication.direction == "inbound")
    )
    inbound_count = result.scalar()
    
    return {
        "by_channel": by_channel,
        "by_status": by_status,
        "total_sent": sum(by_channel.values()),
        "total_received": inbound_count
    }


@router.get("/inbox")
async def get_inbox(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת הודעות נכנסות (Inbox)
    """
    query = (
        select(Communication)
        .where(Communication.direction == "inbound")
        .order_by(Communication.sent_at.desc())
    )
    
    if unread_only:
        query = query.where(Communication.status == "delivered")
    
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    
    return result.scalars().all()


@router.get("/conversation/{lead_id}", response_model=ConversationResponse)
async def get_conversation(
    lead_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת כל השיחה עם ליד ספציפי
    """
    # קבלת פרטי הליד
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # קבלת כל ההודעות
    result = await session.execute(
        select(Communication)
        .where(Communication.lead_id == lead_id)
        .order_by(Communication.sent_at.asc())
    )
    messages = result.scalars().all()
    
    return ConversationResponse(
        lead_id=lead_id,
        domain=lead.domain,
        site_name=lead.site_name,
        messages=messages,
        total_messages=len(messages)
    )


@router.post("/send/whatsapp")
async def send_whatsapp(
    data: MessageCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת הודעת WhatsApp
    """
    if data.channel != "whatsapp":
        data.channel = "whatsapp"
    
    # בדיקה שהליד קיים
    result = await session.execute(
        select(Lead).where(Lead.id == data.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # יצירת רשומת הודעה
    message = Communication(
        lead_id=data.lead_id,
        channel="whatsapp",
        direction="outbound",
        message_body=data.message_body,
        status="pending"
    )
    
    session.add(message)
    await session.flush()
    await session.refresh(message)
    
    # TODO: שליחה בפועל דרך Green-API
    # from app.services.whatsapp_service import send_message
    # result = await send_message(lead.phone, data.message_body)
    
    message.status = "sent"
    
    return {"message": "הודעת WhatsApp נשלחה", "message_id": message.id}


@router.post("/send/email")
async def send_email_endpoint(
    data: MessageCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת Email דרך SendGrid
    """
    # בדיקה שהליד קיים
    result = await session.execute(
        select(Lead).where(Lead.id == data.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    if not data.subject:
        raise HTTPException(status_code=400, detail="חובה לציין נושא למייל")
    
    # קבלת כתובת מייל של הליד
    to_email = None
    if lead.contact_info:
        to_email = lead.contact_info.get("whois_email")
        if not to_email:
            emails = lead.contact_info.get("emails", [])
            if emails:
                to_email = emails[0]
    
    if not to_email:
        raise HTTPException(status_code=400, detail="לליד אין כתובת מייל")
    
    # יצירת רשומת הודעה
    message = Communication(
        lead_id=data.lead_id,
        channel="email",
        direction="outbound",
        message_body=data.message_body,
        subject=data.subject,
        status="pending",
        template_id=data.template_id
    )
    
    session.add(message)
    await session.flush()
    await session.refresh(message)
    
    # שליחה בפועל דרך SMTP (בלי מעקב קליקים - רק מעקב תשובות)
    smtp_service = get_smtp_service()
    result = await smtp_service.send_email_async(
        to_email=to_email,
        subject=data.subject,
        body=data.message_body,
        html_body=data.html_body,
        enable_tracking=False  # כבוי - מעקב רק דרך תשובות IMAP
    )
    
    if result.get("success"):
        message.status = "sent"
        message.external_id = result.get("message_id")
        
        # עדכון סטטוס הליד
        if lead.status in ["new", "matched"]:
            lead.status = "contacted"
            lead.last_contacted_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(f"Email sent to {to_email} for lead {lead.id}")
        return {
            "success": True,
            "message": "Email נשלח בהצלחה",
            "message_id": message.id,
            "external_id": result.get("message_id")
        }
    else:
        message.status = "failed"
        message.error_message = result.get("error")
        await session.commit()
        
        logger.error(f"Email failed for lead {lead.id}: {result.get('error')}")
        raise HTTPException(
            status_code=500, 
            detail=f"שליחת המייל נכשלה: {result.get('error')}"
        )


@router.post("/send/bulk-email")
async def send_bulk_email(
    data: BulkEmailCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת מייל לרשימת לידים
    """
    if not data.lead_ids:
        raise HTTPException(status_code=400, detail="רשימת לידים ריקה")
    
    # קבלת הלידים
    result = await session.execute(
        select(Lead).where(Lead.id.in_(data.lead_ids))
    )
    leads = result.scalars().all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="לא נמצאו לידים")
    
    # בדיקה כמה לידים יש להם מייל
    valid_leads = []
    for lead in leads:
        to_email = None
        if lead.contact_info:
            to_email = lead.contact_info.get("whois_email")
            if not to_email:
                emails = lead.contact_info.get("emails", [])
                if emails:
                    to_email = emails[0]
        if to_email:
            valid_leads.append((lead, to_email))
    
    if not valid_leads:
        raise HTTPException(status_code=400, detail="אף ליד אין לו כתובת מייל")
    
    # שליחה ברקע
    async def send_emails_background():
        smtp_service = get_smtp_service()
        sent_count = 0
        failed_count = 0
        
        for lead, to_email in valid_leads:
            try:
                # יצירת רשומת הודעה
                message = Communication(
                    lead_id=lead.id,
                    channel="email",
                    direction="outbound",
                    message_body=data.message_body,
                    subject=data.subject,
                    status="pending",
                    template_id=data.template_id
                )
                session.add(message)
                await session.flush()
                
                # שליחה
                result = await smtp_service.send_email_async(
                    to_email=to_email,
                    subject=data.subject,
                    body=data.message_body,
                    html_body=data.html_body
                )
                
                if result.get("success"):
                    message.status = "sent"
                    message.external_id = result.get("message_id")
                    if lead.status in ["new", "matched"]:
                        lead.status = "contacted"
                        lead.last_contacted_at = datetime.utcnow()
                    sent_count += 1
                else:
                    message.status = "failed"
                    message.error_message = result.get("error")
                    failed_count += 1
                
                await session.commit()
                
            except Exception as e:
                logger.error(f"Bulk email error for lead {lead.id}: {e}")
                failed_count += 1
        
        logger.info(f"Bulk email completed: {sent_count} sent, {failed_count} failed")
    
    background_tasks.add_task(send_emails_background)
    
    return {
        "message": f"שליחת {len(valid_leads)} מיילים התחילה ברקע",
        "total_leads": len(data.lead_ids),
        "valid_leads": len(valid_leads),
        "skipped": len(data.lead_ids) - len(valid_leads)
    }


@router.post("/reply/{message_id}")
async def reply_to_message(
    message_id: int,
    reply_body: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    תשובה להודעה קיימת
    """
    # קבלת ההודעה המקורית
    result = await session.execute(
        select(Communication).where(Communication.id == message_id)
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="הודעה לא נמצאה")
    
    if original.channel != "email":
        raise HTTPException(status_code=400, detail="ניתן לענות רק על הודעות מייל")
    
    # קבלת הליד
    result = await session.execute(
        select(Lead).where(Lead.id == original.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    # קבלת כתובת מייל
    to_email = None
    if lead.contact_info:
        to_email = lead.contact_info.get("whois_email")
        if not to_email:
            emails = lead.contact_info.get("emails", [])
            if emails:
                to_email = emails[0]
    
    if not to_email:
        raise HTTPException(status_code=400, detail="לליד אין כתובת מייל")
    
    # נושא עם Re:
    subject = original.subject
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
    
    # יצירת רשומת תשובה
    reply = Communication(
        lead_id=original.lead_id,
        channel="email",
        direction="outbound",
        message_body=reply_body,
        subject=subject,
        status="pending",
        thread_id=original.thread_id or str(original.id),
        in_reply_to_id=original.id
    )
    
    session.add(reply)
    await session.flush()
    
    # שליחה
    smtp_service = get_smtp_service()
    result = await smtp_service.send_email_async(
        to_email=to_email,
        subject=subject,
        body=reply_body
    )
    
    if result.get("success"):
        reply.status = "sent"
        reply.external_id = result.get("message_id")
        await session.commit()
        
        return {
            "success": True,
            "message": "תשובה נשלחה",
            "message_id": reply.id
        }
    else:
        reply.status = "failed"
        reply.error_message = result.get("error")
        await session.commit()
        
        raise HTTPException(status_code=500, detail=f"שליחה נכשלה: {result.get('error')}")


@router.post("/send/sms")
async def send_sms(
    data: MessageCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שליחת SMS
    """
    # בדיקה שהליד קיים
    result = await session.execute(
        select(Lead).where(Lead.id == data.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # בדיקת אורך הודעה
    if len(data.message_body) > 160:
        raise HTTPException(status_code=400, detail="הודעת SMS מוגבלת ל-160 תווים")
    
    # יצירת רשומת הודעה
    message = Communication(
        lead_id=data.lead_id,
        channel="sms",
        direction="outbound",
        message_body=data.message_body,
        status="pending"
    )
    
    session.add(message)
    await session.flush()
    await session.refresh(message)
    
    # TODO: שליחה בפועל דרך Twilio
    # from app.services.sms_service import send_sms
    # result = await send_sms(lead.phone, data.message_body)
    
    message.status = "sent"
    
    return {"message": "SMS נשלח", "message_id": message.id}


@router.post("/{message_id}/mark-read")
async def mark_as_read(
    message_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סימון הודעה כנקראה
    """
    result = await session.execute(
        select(Communication).where(Communication.id == message_id)
    )
    message = result.scalar_one_or_none()
    
    if not message:
        raise HTTPException(status_code=404, detail="הודעה לא נמצאה")
    
    message.status = "read"
    message.read_at = datetime.utcnow()
    
    await session.flush()
    
    return {"message": "הודעה סומנה כנקראה"}


# ========== Email Tracking Dashboard ==========

@router.get("/sent-tracking")
async def get_sent_with_tracking(
    status: Optional[str] = Query(None, description="סינון לפי סטטוס: sent, delivered, opened, bounced"),
    search: Optional[str] = Query(None, description="חיפוש לפי מייל או דומיין"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת מיילים שנשלחו עם מידע tracking מלא
    מחזיר: items (רשימת מיילים), stats (סיכום), pagination
    """
    from sqlalchemy import desc, or_
    
    # Base query - join with Lead for domain info
    base_query = select(Communication, Lead).outerjoin(
        Lead, Communication.lead_id == Lead.id
    ).where(
        Communication.channel == "email",
        Communication.direction == "outbound"
    )
    
    # Apply status filter
    if status:
        if status == "opened":
            base_query = base_query.where(Communication.opens_count > 0)
        elif status == "bounced":
            base_query = base_query.where(Communication.status == "failed")
        elif status == "clicked":
            # Using JSON check for clicks array
            base_query = base_query.where(Communication.clicks.isnot(None))
        else:
            base_query = base_query.where(Communication.status == status)
    
    # Apply search filter
    if search:
        base_query = base_query.where(
            or_(
                Communication.recipient.contains(search),
                Lead.domain.contains(search)
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    # Apply ordering and pagination
    query = base_query.order_by(desc(Communication.sent_at))
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)
    
    result = await session.execute(query)
    rows = result.all()
    
    # Build items list
    items = []
    for comm, lead in rows:
        clicks_count = len(comm.clicks) if comm.clicks else 0
        items.append({
            "id": comm.id,
            "lead_id": comm.lead_id,
            "domain": lead.domain if lead else None,
            "to_email": comm.recipient,
            "subject": comm.subject,
            "status": comm.status,
            "sent_at": comm.sent_at.isoformat() if comm.sent_at else None,
            "delivered_at": comm.delivered_at.isoformat() if comm.delivered_at else None,
            "read_at": comm.read_at.isoformat() if comm.read_at else None,
            "opens_count": comm.opens_count or 0,
            "clicks_count": clicks_count,
            "clicks": comm.clicks or [],
            "error_message": comm.error_message
        })
    
    # Calculate stats
    stats = await _get_sent_stats(session)
    
    return {
        "items": items,
        "stats": stats,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total + per_page - 1) // per_page
        }
    }


async def _get_sent_stats(session: AsyncSession) -> dict:
    """
    חישוב סטטיסטיקות מיילים שנשלחו
    """
    from sqlalchemy import desc
    
    # Total sent
    total_result = await session.execute(
        select(func.count(Communication.id)).where(
            Communication.channel == "email",
            Communication.direction == "outbound"
        )
    )
    total = total_result.scalar() or 0
    
    # Delivered (status = sent or delivered)
    delivered_result = await session.execute(
        select(func.count(Communication.id)).where(
            Communication.channel == "email",
            Communication.direction == "outbound",
            Communication.status.in_(["sent", "delivered", "read"])
        )
    )
    delivered = delivered_result.scalar() or 0
    
    # Opened (opens_count > 0)
    opened_result = await session.execute(
        select(func.count(Communication.id)).where(
            Communication.channel == "email",
            Communication.direction == "outbound",
            Communication.opens_count > 0
        )
    )
    opened = opened_result.scalar() or 0
    
    # Clicked (has clicks)
    clicked_result = await session.execute(
        select(func.count(Communication.id)).where(
            Communication.channel == "email",
            Communication.direction == "outbound",
            Communication.clicks.isnot(None)
        )
    )
    clicked = clicked_result.scalar() or 0
    
    # Bounced (status = failed)
    bounced_result = await session.execute(
        select(func.count(Communication.id)).where(
            Communication.channel == "email",
            Communication.direction == "outbound",
            Communication.status == "failed"
        )
    )
    bounced = bounced_result.scalar() or 0
    
    return {
        "total": total,
        "delivered": delivered,
        "opened": opened,
        "clicked": clicked,
        "bounced": bounced,
        "open_rate": round((opened / total * 100), 1) if total > 0 else 0,
        "click_rate": round((clicked / total * 100), 1) if total > 0 else 0,
        "bounce_rate": round((bounced / total * 100), 1) if total > 0 else 0
    }
