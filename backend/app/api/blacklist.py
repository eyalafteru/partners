"""
PartnerCalc OS - Blacklist API
ניהול רשימה שחורה - מיילים/דומיינים שלא לשלוח אליהם
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from loguru import logger

from app.database import get_async_session
from app.models import Blacklist, Lead

router = APIRouter()


# ========== Schemas ==========

class BlacklistAddRequest(BaseModel):
    """בקשה להוספה לרשימה שחורה"""
    email: Optional[str] = None
    domain: Optional[str] = None
    reason: str
    notes: Optional[str] = None
    source: str = "manual"


class BlacklistBulkAddRequest(BaseModel):
    """בקשה להוספת מספר רשומות"""
    items: List[BlacklistAddRequest]


# ========== Endpoints ==========

@router.get("")
async def get_blacklist(
    search: Optional[str] = Query(None, description="חיפוש לפי מייל/דומיין"),
    reason: Optional[str] = Query(None, description="סינון לפי סיבה"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת רשימה שחורה"""
    query = select(Blacklist)
    
    if search:
        query = query.where(
            or_(
                Blacklist.email.contains(search),
                Blacklist.domain.contains(search)
            )
        )
    
    if reason:
        query = query.where(Blacklist.reason == reason)
    
    query = query.order_by(Blacklist.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    # Count total
    count_query = select(func.count(Blacklist.id))
    if search:
        count_query = count_query.where(
            or_(
                Blacklist.email.contains(search),
                Blacklist.domain.contains(search)
            )
        )
    if reason:
        count_query = count_query.where(Blacklist.reason == reason)
    
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    
    return {
        "items": [
            {
                "id": item.id,
                "email": item.email,
                "domain": item.domain,
                "reason": item.reason,
                "notes": item.notes,
                "source": item.source,
                "created_at": item.created_at.isoformat() if item.created_at else None
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("")
async def add_to_blacklist(
    request: BlacklistAddRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """הוספה לרשימה שחורה"""
    if not request.email and not request.domain:
        raise HTTPException(
            status_code=400, 
            detail="Must provide either email or domain"
        )
    
    # Check if already exists
    if request.email:
        existing = await session.execute(
            select(Blacklist).where(Blacklist.email == request.email)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"Email {request.email} is already blacklisted"
            )
    
    # Create blacklist entry
    entry = Blacklist(
        email=request.email,
        domain=request.domain,
        reason=request.reason,
        notes=request.notes,
        source=request.source
    )
    session.add(entry)
    
    # Update lead status if email matches
    if request.email:
        lead_result = await session.execute(
            select(Lead).where(
                Lead.contact_info.contains(request.email)
            )
        )
        leads = lead_result.scalars().all()
        for lead in leads:
            if lead.email == request.email:
                lead.status = "blacklisted"
                logger.info(f"Lead {lead.domain} marked as blacklisted")
    
    # Update leads with matching domain
    if request.domain:
        lead_result = await session.execute(
            select(Lead).where(Lead.domain == request.domain)
        )
        lead = lead_result.scalar_one_or_none()
        if lead:
            lead.status = "blacklisted"
            logger.info(f"Lead {lead.domain} marked as blacklisted")
    
    await session.commit()
    
    return {
        "status": "added",
        "id": entry.id,
        "email": entry.email,
        "domain": entry.domain
    }


@router.post("/bulk")
async def bulk_add_to_blacklist(
    request: BlacklistBulkAddRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """הוספת מספר רשומות לרשימה שחורה"""
    added = 0
    skipped = 0
    
    for item in request.items:
        if not item.email and not item.domain:
            skipped += 1
            continue
        
        # Check if exists
        if item.email:
            existing = await session.execute(
                select(Blacklist).where(Blacklist.email == item.email)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
        
        entry = Blacklist(
            email=item.email,
            domain=item.domain,
            reason=item.reason,
            notes=item.notes,
            source=item.source
        )
        session.add(entry)
        added += 1
    
    await session.commit()
    
    return {
        "status": "success",
        "added": added,
        "skipped": skipped
    }


@router.delete("/{blacklist_id}")
async def remove_from_blacklist(
    blacklist_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """הסרה מרשימה שחורה"""
    result = await session.execute(
        select(Blacklist).where(Blacklist.id == blacklist_id)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    
    email = entry.email
    domain = entry.domain
    
    await session.delete(entry)
    
    # Update lead status back to matched if was blacklisted
    if email:
        lead_result = await session.execute(
            select(Lead).where(
                Lead.status == "blacklisted"
            )
        )
        leads = lead_result.scalars().all()
        for lead in leads:
            if lead.email == email:
                lead.status = "matched"
                logger.info(f"Lead {lead.domain} status restored to matched")
    
    if domain:
        lead_result = await session.execute(
            select(Lead).where(
                Lead.domain == domain,
                Lead.status == "blacklisted"
            )
        )
        lead = lead_result.scalar_one_or_none()
        if lead:
            lead.status = "matched"
            logger.info(f"Lead {lead.domain} status restored to matched")
    
    await session.commit()
    
    return {"status": "removed", "id": blacklist_id}


@router.get("/check")
async def check_blacklist(
    email: Optional[str] = None,
    domain: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """בדיקה אם מייל/דומיין ברשימה שחורה"""
    if not email and not domain:
        raise HTTPException(
            status_code=400,
            detail="Must provide either email or domain"
        )
    
    conditions = []
    if email:
        conditions.append(Blacklist.email == email)
    if domain:
        conditions.append(Blacklist.domain == domain)
    
    result = await session.execute(
        select(Blacklist).where(or_(*conditions))
    )
    entry = result.scalar_one_or_none()
    
    if entry:
        return {
            "blacklisted": True,
            "reason": entry.reason,
            "match_type": "email" if entry.email == email else "domain",
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        }
    
    return {"blacklisted": False}


@router.get("/reasons")
async def get_blacklist_reasons(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת סיבות חסימה אפשריות"""
    return {
        "reasons": [
            {"value": "bounced", "label": "מייל חזר"},
            {"value": "unsubscribed", "label": "ביקש להסרה"},
            {"value": "spam_complaint", "label": "התלונן על ספאם"},
            {"value": "invalid_email", "label": "מייל לא תקין"},
            {"value": "competitor", "label": "מתחרה"},
            {"value": "not_relevant", "label": "לא רלוונטי"},
            {"value": "manual", "label": "הוספה ידנית"}
        ]
    }
