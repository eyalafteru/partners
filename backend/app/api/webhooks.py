"""
PartnerCalc OS - Webhooks API
קבלת הודעות נכנסות מ-WhatsApp, Email, SMS
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

from app.database import get_async_session
from app.models.communication import Communication
from app.models.lead import Lead
from app.models import Blacklist

router = APIRouter()

LEAD_HUNTER_APPROVAL_PHONE = "0542575412"


def _normalize_phone(raw: str) -> str:
    """נרמול מספר טלפון: 972542575412@c.us -> 0542575412"""
    phone = raw.replace("@c.us", "").replace("@g.us", "").replace("+", "")
    if phone.startswith("972") and len(phone) > 3:
        phone = "0" + phone[3:]
    return phone


async def _handle_lead_hunter_approval(message: str, session: AsyncSession) -> dict | None:
    """
    טיפול בהודעות אישור/דחייה של Lead Hunter.
    מחזיר dict תשובה אם טופל, או None אם לא רלוונטי.
    """
    text = message.strip()
    if text not in ("1", "0"):
        return None

    from app.models.lead_hunter import LeadPost

    result = await session.execute(
        select(LeadPost)
        .where(LeadPost.auto_reply_status == "awaiting_approval")
        .order_by(LeadPost.created_at.asc())
        .limit(1)
    )
    post = result.scalar_one_or_none()

    if not post:
        from app.services.whatsapp_service import get_whatsapp_service
        ws = get_whatsapp_service()
        if ws.is_configured:
            await ws.send_to_phone(LEAD_HUNTER_APPROVAL_PHONE, "אין תגובות ממתינות לאישור כרגע.")
        logger.info("🎯 Lead Hunter approval: no posts awaiting approval")
        return {"status": "no_posts_awaiting"}

    from app.services.whatsapp_service import get_whatsapp_service
    ws = get_whatsapp_service()

    if text == "1":
        post.auto_reply_status = "pending"
        await session.commit()
        logger.info(f"🎯 ✅ Lead Hunter approval: post {post.id} APPROVED -> pending")
        if ws.is_configured:
            await ws.send_to_phone(
                LEAD_HUNTER_APPROVAL_PHONE,
                f"✅ אושר! פוסט #{post.id} עובר לפרסום."
            )
        return {"status": "approved", "post_id": post.id}

    else:  # text == "0"
        post.auto_reply_status = "skipped"
        await session.commit()
        logger.info(f"🎯 ❌ Lead Hunter approval: post {post.id} REJECTED -> skipped")
        if ws.is_configured:
            await ws.send_to_phone(
                LEAD_HUNTER_APPROVAL_PHONE,
                f"❌ נדחה. פוסט #{post.id} לא יפורסם."
            )
        return {"status": "rejected", "post_id": post.id}


# ========== Green-API WhatsApp Webhook ==========

@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook לקבלת הודעות WhatsApp מ-Green-API
    
    Green-API שולח:
    {
        "typeWebhook": "incomingMessageReceived",
        "instanceData": {...},
        "timestamp": 1234567890,
        "idMessage": "...",
        "senderData": {
            "chatId": "972501234567@c.us",
            "sender": "972501234567@c.us",
            "senderName": "יוסי"
        },
        "messageData": {
            "typeMessage": "textMessage",
            "textMessageData": {
                "textMessage": "היי, קיבלתי את ההודעה..."
            }
        }
    }
    """
    try:
        payload = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # בדיקת סוג ה-webhook
    webhook_type = payload.get("typeWebhook")
    
    if webhook_type == "incomingMessageReceived":
        # הודעה נכנסת
        sender_data = payload.get("senderData", {})
        message_data = payload.get("messageData", {})
        
        # חילוץ מספר טלפון
        chat_id = sender_data.get("chatId", "")
        phone = chat_id.replace("@c.us", "").replace("@g.us", "")
        
        # חילוץ תוכן ההודעה
        text_data = message_data.get("textMessageData", {})
        message_body = text_data.get("textMessage", "")
        
        if not message_body:
            # אולי הודעת מדיה
            return {"status": "ignored", "reason": "not text message"}
        
        # --- Lead Hunter: אישור/דחייה דרך WhatsApp ---
        sender_normalized = _normalize_phone(chat_id)
        if sender_normalized == LEAD_HUNTER_APPROVAL_PHONE:
            approval_result = await _handle_lead_hunter_approval(message_body, session)
            if approval_result is not None:
                return approval_result
        
        # חיפוש הליד לפי טלפון
        result = await session.execute(
            select(Lead).where(
                Lead.contact_info["phones"].astext.contains(phone)
            )
        )
        lead = result.scalar_one_or_none()
        
        if not lead:
            # ליד לא נמצא - יצירת ליד חדש או התעלמות
            return {"status": "no_lead_found", "phone": phone}
        
        # שמירת ההודעה
        communication = Communication(
            lead_id=lead.id,
            channel="whatsapp",
            direction="inbound",
            message_body=message_body,
            status="delivered",
            external_id=payload.get("idMessage"),
            sent_at=datetime.utcnow()
        )
        
        session.add(communication)
        
        # עדכון סטטוס הליד
        if lead.status == "contacted":
            lead.status = "responded"
        
        await session.flush()
        
        # Auto-Reply - אם מופעל, יצירת הצעת תגובה
        try:
            from app.services.ai_reply_service import handle_incoming_whatsapp
            await handle_incoming_whatsapp(communication, session)
        except ImportError:
            logger.debug("WhatsApp auto-reply handler not yet implemented")
        except Exception as e:
            logger.error(f"WhatsApp auto-reply error: {e}")
        
        return {
            "status": "saved",
            "lead_id": lead.id,
            "message_id": communication.id
        }
    
    elif webhook_type == "outgoingMessageStatus":
        # עדכון סטטוס הודעה יוצאת
        status = payload.get("status")
        external_id = payload.get("idMessage")
        
        if external_id:
            result = await session.execute(
                select(Communication).where(Communication.external_id == external_id)
            )
            comm = result.scalar_one_or_none()
            
            if comm:
                if status == "delivered":
                    comm.status = "delivered"
                    comm.delivered_at = datetime.utcnow()
                elif status == "read":
                    comm.status = "read"
                    comm.read_at = datetime.utcnow()
                
                await session.flush()
        
        return {"status": "updated"}
    
    return {"status": "ignored"}


# ========== SendGrid Email Webhook ==========

@router.post("/email")
async def email_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook לקבלת אירועי Email מ-SendGrid
    
    SendGrid שולח מערך של אירועים:
    [
        {
            "email": "example@domain.com",
            "event": "open",
            "timestamp": 1234567890,
            "sg_message_id": "...",
            "url": "..." (for click events)
        }
    ]
    """
    from loguru import logger
    
    try:
        events = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    if not isinstance(events, list):
        events = [events]
    
    processed = 0
    for event in events:
        event_type = event.get("event")
        message_id = event.get("sg_message_id", "").split(".")[0]  # SendGrid מוסיף suffix
        
        if not message_id:
            continue
        
        result = await session.execute(
            select(Communication).where(
                Communication.external_id == message_id,
                Communication.channel == "email"
            )
        )
        comm = result.scalar_one_or_none()
        
        if not comm:
            logger.warning(f"Email webhook: message not found for {message_id}")
            continue
        
        processed += 1
        
        if event_type == "delivered":
            comm.status = "delivered"
            comm.delivered_at = datetime.utcnow()
            logger.info(f"Email delivered: {message_id}")
            
        elif event_type == "open":
            # ספירת פתיחות
            comm.opens_count = (comm.opens_count or 0) + 1
            if not comm.read_at:
                comm.status = "read"
                comm.read_at = datetime.utcnow()
            logger.info(f"Email opened: {message_id} (count: {comm.opens_count})")
            
        elif event_type == "click":
            # שמירת לינקים שנלחצו
            url = event.get("url", "")
            if url:
                clicks = comm.clicks or []
                clicks.append({
                    "url": url,
                    "timestamp": datetime.utcnow().isoformat()
                })
                comm.clicks = clicks
            logger.info(f"Email click: {message_id} - {url}")
            
        elif event_type in ["bounce", "dropped"]:
            comm.status = "failed"
            comm.error_message = f"{event_type}: {event.get('reason', '')}"
            logger.warning(f"Email {event_type}: {message_id}")
            
            # AUTO-BLACKLIST bounced emails
            email = event.get("email")
            if email:
                # Check if not already blacklisted
                existing = await session.execute(
                    select(Blacklist).where(Blacklist.email == email)
                )
                if not existing.scalar_one_or_none():
                    entry = Blacklist(
                        email=email,
                        reason="bounced",
                        source="auto_bounce",
                        notes=f"Auto: {event_type} - {event.get('reason', '')}"
                    )
                    session.add(entry)
                    
                    # Update lead status to bounced
                    if comm.lead_id:
                        lead_result = await session.execute(
                            select(Lead).where(Lead.id == comm.lead_id)
                        )
                        lead = lead_result.scalar_one_or_none()
                        if lead:
                            lead.status = "bounced"
                    
                    logger.info(f"Auto-blacklisted bounced email: {email}")
            
        elif event_type == "spamreport":
            comm.status = "failed"
            comm.error_message = "spam_report"
            logger.warning(f"Email spam report: {message_id}")
            
            # AUTO-BLACKLIST spam reporters
            email = event.get("email")
            if email:
                existing = await session.execute(
                    select(Blacklist).where(Blacklist.email == email)
                )
                if not existing.scalar_one_or_none():
                    entry = Blacklist(
                        email=email,
                        reason="spam_complaint",
                        source="auto_spam",
                        notes="Auto: User reported as spam"
                    )
                    session.add(entry)
                    
                    if comm.lead_id:
                        lead_result = await session.execute(
                            select(Lead).where(Lead.id == comm.lead_id)
                        )
                        lead = lead_result.scalar_one_or_none()
                        if lead:
                            lead.status = "blacklisted"
                    
                    logger.info(f"Auto-blacklisted spam reporter: {email}")
    
    await session.commit()
    
    return {"status": "processed", "events_count": len(events), "processed": processed}


# ========== SendGrid Inbound Parse Webhook ==========

@router.post("/email/inbound")
async def email_inbound_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook לקבלת מיילים נכנסים מ-SendGrid Inbound Parse
    
    SendGrid שולח (multipart form):
    - from: שולח
    - to: נמען (אנחנו)
    - subject: נושא
    - text: תוכן טקסט
    - html: תוכן HTML
    - headers: כותרות מלאות
    """
    from loguru import logger
    
    try:
        form = await request.form()
    except:
        raise HTTPException(status_code=400, detail="Invalid form data")
    
    from_email = form.get("from", "")
    to_email = form.get("to", "")
    subject = form.get("subject", "")
    text_body = form.get("text", "")
    html_body = form.get("html", "")
    
    # חילוץ כתובת המייל בלבד
    import re
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_email)
    if email_match:
        from_email = email_match.group()
    
    logger.info(f"Inbound email from {from_email}: {subject}")
    
    if not from_email or not text_body:
        return {"status": "ignored", "reason": "missing data"}
    
    # חיפוש ליד לפי מייל
    result = await session.execute(
        select(Lead).where(
            Lead.contact_info["whois_email"].astext == from_email
        )
    )
    lead = result.scalar_one_or_none()
    
    # אם לא נמצא - חפש במערך emails
    if not lead:
        result = await session.execute(
            select(Lead).where(
                Lead.contact_info["emails"].astext.contains(from_email)
            )
        )
        lead = result.scalar_one_or_none()
    
    if not lead:
        logger.warning(f"Inbound email: no lead found for {from_email}")
        return {"status": "no_lead_found", "email": from_email}
    
    # חיפוש הודעה קודמת לקישור thread
    thread_id = None
    in_reply_to_id = None
    
    # חפש הודעות יוצאות קודמות לאותו ליד
    result = await session.execute(
        select(Communication)
        .where(
            Communication.lead_id == lead.id,
            Communication.channel == "email",
            Communication.direction == "outbound"
        )
        .order_by(Communication.sent_at.desc())
        .limit(1)
    )
    last_outbound = result.scalar_one_or_none()
    
    if last_outbound:
        thread_id = last_outbound.thread_id or str(last_outbound.id)
        in_reply_to_id = last_outbound.id
    
    # שמירת ההודעה הנכנסת
    communication = Communication(
        lead_id=lead.id,
        channel="email",
        direction="inbound",
        message_body=text_body,
        subject=subject,
        status="delivered",
        thread_id=thread_id,
        in_reply_to_id=in_reply_to_id,
        sent_at=datetime.utcnow()
    )
    
    session.add(communication)
    
    # עדכון סטטוס הליד
    if lead.status == "contacted":
        lead.status = "responded"
    
    await session.commit()
    
    logger.info(f"Inbound email saved: lead={lead.id}, message={communication.id}")
    
    # הפעלת Auto-Reply אם מופעל
    try:
        from app.services.ai_reply_service import handle_incoming_email
        await handle_incoming_email(communication, session)
    except Exception as e:
        logger.error(f"Auto-reply error: {e}")
    
    return {
        "status": "saved",
        "lead_id": lead.id,
        "message_id": communication.id
    }


# ========== Twilio SMS Webhook ==========

@router.post("/sms")
async def sms_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook לקבלת SMS נכנס מ-Twilio
    
    Twilio שולח:
    {
        "MessageSid": "...",
        "From": "+972501234567",
        "To": "+972...",
        "Body": "תוכן ההודעה"
    }
    """
    form_data = await request.form()
    
    message_sid = form_data.get("MessageSid")
    from_number = form_data.get("From", "").replace("+", "")
    body = form_data.get("Body", "")
    
    if not body:
        return {"status": "ignored"}
    
    # חיפוש הליד לפי טלפון
    result = await session.execute(
        select(Lead).where(
            Lead.contact_info["phones"].astext.contains(from_number)
        )
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        return {"status": "no_lead_found", "phone": from_number}
    
    # שמירת ההודעה
    communication = Communication(
        lead_id=lead.id,
        channel="sms",
        direction="inbound",
        message_body=body,
        status="delivered",
        external_id=message_sid,
        sent_at=datetime.utcnow()
    )
    
    session.add(communication)
    
    # עדכון סטטוס הליד
    if lead.status == "contacted":
        lead.status = "responded"
    
    await session.flush()
    
    return {
        "status": "saved",
        "lead_id": lead.id,
        "message_id": communication.id
    }


# ========== SMS Status Callback ==========

@router.post("/sms/status")
async def sms_status_webhook(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Webhook לעדכון סטטוס SMS מ-Twilio
    """
    form_data = await request.form()
    
    message_sid = form_data.get("MessageSid")
    status = form_data.get("MessageStatus")
    
    if not message_sid:
        return {"status": "ignored"}
    
    result = await session.execute(
        select(Communication).where(
            Communication.external_id == message_sid,
            Communication.channel == "sms"
        )
    )
    comm = result.scalar_one_or_none()
    
    if comm:
        if status == "delivered":
            comm.status = "delivered"
            comm.delivered_at = datetime.utcnow()
        elif status in ["failed", "undelivered"]:
            comm.status = "failed"
            comm.error_message = form_data.get("ErrorMessage", status)
        
        await session.flush()
    
    return {"status": "updated"}
