"""
PartnerCalc OS - AI Reply API
ניהול תשובות AI ממתינות לאישור
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_async_session
from app.models.auto_reply import PendingReply, AutoReply
from app.models.communication import Communication
from app.models.lead import Lead
from app.services.smtp_service import get_smtp_service
from app.services.ai_reply_service import get_ai_reply_service

router = APIRouter()


# ========== Pydantic Schemas ==========

class PendingReplyResponse(BaseModel):
    """סכמה לתשובה ממתינה"""
    id: int
    communication_id: Optional[int] = None
    lead_id: Optional[int] = None
    suggested_reply: str
    suggested_subject: Optional[str] = None
    ai_reasoning: Optional[str]
    status: str
    created_at: Optional[datetime]
    
    # Scenario info
    scenario_name: Optional[str] = None
    scenario_category: Optional[str] = None
    match_confidence: Optional[str] = None
    match_method: Optional[str] = None
    
    # Original message info
    original_message: Optional[str] = None
    original_subject: Optional[str] = None
    sender_email: Optional[str] = None
    lead_domain: Optional[str] = None
    
    class Config:
        from_attributes = True


class EditReplyRequest(BaseModel):
    """סכמה לעריכת תשובה"""
    reply_text: str


class GenerateReplyRequest(BaseModel):
    """סכמה ליצירת תשובה"""
    communication_id: int


# ========== API Endpoints ==========

@router.get("/pending", response_model=List[PendingReplyResponse])
async def list_pending_replies(
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת תשובות ממתינות לאישור
    """
    result = await session.execute(
        select(PendingReply)
        .where(PendingReply.status == "pending")
        .order_by(PendingReply.created_at.desc())
    )
    pending_list = result.scalars().all()
    
    response = []
    for pending in pending_list:
        lead_domain = None
        sender_email = pending.sender_email  # Use stored sender email first
        original_message = pending.trigger_message  # Use stored trigger message
        original_subject = pending.trigger_subject  # Use stored trigger subject
        
        # Get additional info from communication if available
        if pending.communication_id:
            comm_result = await session.execute(
                select(Communication).where(Communication.id == pending.communication_id)
            )
            comm = comm_result.scalar_one_or_none()
            
            if comm:
                if not original_message:
                    original_message = comm.message_body
                if not original_subject:
                    original_subject = comm.subject
                
                # Get lead
                lead_result = await session.execute(
                    select(Lead).where(Lead.id == comm.lead_id)
                )
                lead = lead_result.scalar_one_or_none()
                
                if lead:
                    lead_domain = lead.domain
                    if not sender_email and lead.contact_info:
                        sender_email = lead.contact_info.get("whois_email")
        
        # Fallback: get lead from lead_id
        if not lead_domain and pending.lead_id:
            lead_result = await session.execute(
                select(Lead).where(Lead.id == pending.lead_id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead:
                lead_domain = lead.domain
                if not sender_email and lead.contact_info:
                    sender_email = lead.contact_info.get("whois_email")
        
        response.append(PendingReplyResponse(
            id=pending.id,
            communication_id=pending.communication_id,
            lead_id=pending.lead_id,
            suggested_reply=pending.suggested_reply,
            suggested_subject=pending.suggested_subject,
            ai_reasoning=pending.ai_reasoning,
            status=pending.status,
            created_at=pending.created_at,
            scenario_name=pending.scenario_name,
            scenario_category=pending.scenario_category,
            match_confidence=pending.match_confidence,
            match_method=pending.match_method,
            original_message=original_message,
            original_subject=original_subject,
            sender_email=sender_email,
            lead_domain=lead_domain
        ))
    
    return response


@router.get("/stats")
async def pending_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות תשובות AI
    """
    # Count by status
    result = await session.execute(
        select(PendingReply.status, func.count(PendingReply.id))
        .group_by(PendingReply.status)
    )
    by_status = {row[0]: row[1] for row in result.all()}
    
    return {
        "pending": by_status.get("pending", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "auto_sent": by_status.get("auto_sent", 0)
    }


@router.post("/{pending_id}/approve")
async def approve_reply(
    pending_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    אישור ושליחת תשובה
    """
    # Get pending reply
    result = await session.execute(
        select(PendingReply).where(PendingReply.id == pending_id)
    )
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="תשובה ממתינה לא נמצאה")
    
    if pending.status != "pending":
        raise HTTPException(status_code=400, detail="התשובה כבר טופלה")
    
    # Get lead - either from pending.lead_id or from communication
    lead = None
    original = None
    
    if pending.communication_id:
        result = await session.execute(
            select(Communication).where(Communication.id == pending.communication_id)
        )
        original = result.scalar_one_or_none()
        if original:
            result = await session.execute(
                select(Lead).where(Lead.id == original.lead_id)
            )
            lead = result.scalar_one_or_none()
    
    if not lead and pending.lead_id:
        result = await session.execute(
            select(Lead).where(Lead.id == pending.lead_id)
        )
        lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # Get recipient email - use stored sender_email first
    to_email = pending.sender_email
    if not to_email and lead.contact_info:
        to_email = lead.contact_info.get("whois_email")
        if not to_email:
            emails = lead.contact_info.get("emails", [])
            if emails:
                to_email = emails[0]
    
    if not to_email:
        raise HTTPException(status_code=400, detail="לליד אין כתובת מייל")
    
    # Use suggested subject from pending, or create from original
    subject = pending.suggested_subject
    if not subject:
        original_subject = pending.trigger_subject or (original.subject if original else "")
        subject = f"Re: {original_subject}" if original_subject and not original_subject.startswith("Re:") else original_subject or "תגובה"
    
    # Create reply communication
    reply_comm = Communication(
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        message_body=pending.suggested_reply,
        subject=subject,
        status="pending",
        is_auto_reply=True,
        thread_id=str(original.id) if original else None,
        in_reply_to_id=original.id if original else None
    )
    session.add(reply_comm)
    await session.flush()
    
    # Send email
    smtp_service = get_smtp_service()
    send_result = await smtp_service.send_email_async(
        to_email=to_email,
        subject=subject,
        body=pending.suggested_reply
    )
    
    if send_result.get("success"):
        reply_comm.status = "sent"
        reply_comm.external_id = send_result.get("message_id")
        pending.status = "approved"
        pending.processed_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "success": True,
            "message": "תשובה נשלחה בהצלחה",
            "message_id": reply_comm.id
        }
    else:
        reply_comm.status = "failed"
        reply_comm.error_message = send_result.get("error")
        await session.commit()
        
        raise HTTPException(
            status_code=500, 
            detail=f"שליחה נכשלה: {send_result.get('error')}"
        )


@router.post("/{pending_id}/edit")
async def edit_and_send_reply(
    pending_id: int,
    data: EditReplyRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עריכת תשובה ושליחה
    """
    # Get pending reply
    result = await session.execute(
        select(PendingReply).where(PendingReply.id == pending_id)
    )
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="תשובה ממתינה לא נמצאה")
    
    if pending.status != "pending":
        raise HTTPException(status_code=400, detail="התשובה כבר טופלה")
    
    # Update the reply text
    pending.suggested_reply = data.reply_text
    
    # Get lead - either from pending.lead_id or from communication
    lead = None
    original = None
    
    if pending.communication_id:
        result = await session.execute(
            select(Communication).where(Communication.id == pending.communication_id)
        )
        original = result.scalar_one_or_none()
        if original:
            result = await session.execute(
                select(Lead).where(Lead.id == original.lead_id)
            )
            lead = result.scalar_one_or_none()
    
    if not lead and pending.lead_id:
        result = await session.execute(
            select(Lead).where(Lead.id == pending.lead_id)
        )
        lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # Get recipient email - use stored sender_email first
    to_email = pending.sender_email
    if not to_email and lead.contact_info:
        to_email = lead.contact_info.get("whois_email")
        if not to_email:
            emails = lead.contact_info.get("emails", [])
            if emails:
                to_email = emails[0]
    
    if not to_email:
        raise HTTPException(status_code=400, detail="לליד אין כתובת מייל")
    
    # Use suggested subject from pending, or create from original
    subject = pending.suggested_subject
    if not subject:
        original_subject = pending.trigger_subject or (original.subject if original else "")
        subject = f"Re: {original_subject}" if original_subject and not original_subject.startswith("Re:") else original_subject or "תגובה"
    
    # Create reply communication
    reply_comm = Communication(
        lead_id=lead.id,
        channel="email",
        direction="outbound",
        message_body=data.reply_text,
        subject=subject,
        status="pending",
        is_auto_reply=False,  # Edited by human
        thread_id=str(original.id) if original else None,
        in_reply_to_id=original.id if original else None
    )
    session.add(reply_comm)
    await session.flush()
    
    # Send email
    smtp_service = get_smtp_service()
    send_result = await smtp_service.send_email_async(
        to_email=to_email,
        subject=subject,
        body=data.reply_text
    )
    
    if send_result.get("success"):
        reply_comm.status = "sent"
        reply_comm.external_id = send_result.get("message_id")
        pending.status = "approved"
        pending.processed_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "success": True,
            "message": "תשובה מעודכנת נשלחה בהצלחה",
            "message_id": reply_comm.id
        }
    else:
        reply_comm.status = "failed"
        reply_comm.error_message = send_result.get("error")
        await session.commit()
        
        raise HTTPException(
            status_code=500, 
            detail=f"שליחה נכשלה: {send_result.get('error')}"
        )


@router.post("/{pending_id}/reject")
async def reject_reply(
    pending_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    דחיית תשובה
    """
    result = await session.execute(
        select(PendingReply).where(PendingReply.id == pending_id)
    )
    pending = result.scalar_one_or_none()
    
    if not pending:
        raise HTTPException(status_code=404, detail="תשובה ממתינה לא נמצאה")
    
    if pending.status != "pending":
        raise HTTPException(status_code=400, detail="התשובה כבר טופלה")
    
    pending.status = "rejected"
    pending.processed_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "תשובה נדחתה"}


@router.post("/generate")
async def generate_reply_for_message(
    data: GenerateReplyRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת תשובה AI להודעה ספציפית (ידני) - משתמש בתרחישים
    """
    from app.services.scenario_matcher import match_and_prepare_reply
    from app.database import SessionLocal
    
    # Get communication
    result = await session.execute(
        select(Communication).where(Communication.id == data.communication_id)
    )
    comm = result.scalar_one_or_none()
    
    if not comm:
        raise HTTPException(status_code=404, detail="הודעה לא נמצאה")
    
    # Get lead
    result = await session.execute(
        select(Lead).where(Lead.id == comm.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # Get sender email
    sender_email = None
    if lead.contact_info:
        sender_email = lead.contact_info.get("whois_email")
        if not sender_email:
            emails = lead.contact_info.get("emails", [])
            if emails:
                sender_email = emails[0]
    
    # Get lead name
    lead_name = "שלום"
    if lead.contact_info:
        lead_name = lead.contact_info.get("name") or lead.contact_info.get("whois_name") or "שלום"
    
    # Match scenario using sync session
    with SessionLocal() as sync_session:
        reply_data = await match_and_prepare_reply(
            db=sync_session,
            email_subject=comm.subject or "",
            email_body=comm.message_body or "",
            lead_name=lead_name,
            lead_domain=lead.domain
        )
    
    if not reply_data.get("matched"):
        raise HTTPException(
            status_code=404, 
            detail="לא נמצא תרחיש מתאים להודעה זו"
        )
    
    # Create subject
    response_subject = reply_data.get("response_subject", "")
    if not response_subject:
        response_subject = f"Re: {comm.subject}" if comm.subject else "תגובה"
    
    # Build reasoning
    reasoning_parts = [
        f"תרחיש: {reply_data.get('scenario_display_name', reply_data['scenario_name'])}",
        f"קטגוריה: {reply_data['scenario_category']}",
        f"שיטת זיהוי: {reply_data['method']}",
        f"ביטחון: {reply_data['confidence']:.0%}",
    ]
    ai_reasoning = " | ".join(reasoning_parts)
    
    # Create pending reply
    pending = PendingReply(
        communication_id=comm.id,
        lead_id=lead.id,
        scenario_name=reply_data["scenario_name"],
        scenario_category=reply_data["scenario_category"],
        match_confidence=f"{reply_data['confidence']:.0%}",
        match_method=reply_data["method"],
        suggested_subject=response_subject,
        suggested_reply=reply_data["response_body"],
        ai_reasoning=ai_reasoning,
        trigger_message=comm.message_body[:1000] if comm.message_body else "",
        trigger_subject=comm.subject,
        sender_email=sender_email,
        status="pending"
    )
    session.add(pending)
    await session.commit()
    
    return {
        "success": True,
        "pending_id": pending.id,
        "scenario": reply_data["scenario_name"],
        "reply": reply_data["response_body"],
        "reasoning": ai_reasoning
    }
