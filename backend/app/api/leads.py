"""
PartnerCalc OS - Leads API
CRUD פעולות ללידים
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_async_session
from app.models.lead import Lead
from app.models.calculator import Calculator

router = APIRouter()


# ========== Pydantic Schemas ==========

class LeadCreate(BaseModel):
    """סכמה ליצירת ליד"""
    domain: str
    site_name: Optional[str] = None
    category: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = {}
    seo_data: Optional[Dict[str, Any]] = {}
    source_url: Optional[str] = None


class LeadUpdate(BaseModel):
    """סכמה לעדכון ליד"""
    site_name: Optional[str] = None
    category: Optional[str] = None
    contact_info: Optional[Dict[str, Any]] = None
    seo_data: Optional[Dict[str, Any]] = None
    ai_status: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    recommended_calc_id: Optional[int] = None


class LeadResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    domain: str
    site_name: Optional[str]
    category: Optional[str]
    contact_info: Optional[Dict[str, Any]]
    seo_data: Optional[Dict[str, Any]]
    ai_status: Optional[Dict[str, Any]]
    status: str
    recommended_calc_id: Optional[int]
    recommended_calc_name: Optional[str] = None
    source_url: Optional[str]
    source_campaign_id: Optional[int] = None
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """סכמה לרשימת לידים עם pagination"""
    items: List[LeadResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ========== API Endpoints ==========

@router.get("/", response_model=LeadListResponse)
async def list_leads(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת לידים עם pagination וסינון
    """
    query = select(Lead)
    count_query = select(func.count(Lead.id))
    
    # סינונים
    filters = []
    if status:
        filters.append(Lead.status == status)
    if category:
        filters.append(Lead.category == category)
    if search:
        filters.append(Lead.domain.ilike(f"%{search}%"))
    
    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
    
    # ספירה כוללת
    result = await session.execute(count_query)
    total = result.scalar()
    
    # Pagination
    offset = (page - 1) * per_page
    query = query.order_by(Lead.created_at.desc()).offset(offset).limit(per_page)
    
    result = await session.execute(query)
    leads = result.scalars().all()
    
    # Get calculator names
    calc_ids = [l.recommended_calc_id for l in leads if l.recommended_calc_id]
    calc_names = {}
    if calc_ids:
        calc_result = await session.execute(
            select(Calculator.id, Calculator.name).where(Calculator.id.in_(calc_ids))
        )
        calc_names = {row.id: row.name for row in calc_result.all()}
    
    # Build response with calculator names
    items = []
    for lead in leads:
        lead_dict = {
            "id": lead.id,
            "domain": lead.domain,
            "site_name": lead.site_name,
            "category": lead.category,
            "contact_info": lead.contact_info,
            "seo_data": lead.seo_data,
            "ai_status": lead.ai_status,
            "status": lead.status,
            "recommended_calc_id": lead.recommended_calc_id,
            "recommended_calc_name": calc_names.get(lead.recommended_calc_id) if lead.recommended_calc_id else None,
            "source_url": lead.source_url,
            "source_campaign_id": lead.source_campaign_id,
            "created_at": lead.created_at
        }
        items.append(LeadResponse(**lead_dict))
    
    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/stats")
async def lead_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות לידים לפי סטטוס
    """
    result = await session.execute(
        select(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
    )
    
    stats = {row[0]: row[1] for row in result.all()}
    
    # הוספת סיכום
    stats["total"] = sum(stats.values())
    
    return stats


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת קטגוריות
    """
    result = await session.execute(
        select(Lead.category, func.count(Lead.id))
        .where(Lead.category.isnot(None))
        .group_by(Lead.category)
        .order_by(func.count(Lead.id).desc())
    )
    
    return [{"category": row[0], "count": row[1]} for row in result.all()]


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת ליד לפי ID
    """
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    return lead


@router.post("/", response_model=LeadResponse)
async def create_lead(
    data: LeadCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת ליד חדש
    """
    # בדיקה אם הדומיין כבר קיים
    existing = await session.execute(
        select(Lead).where(Lead.domain == data.domain)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="דומיין כבר קיים במערכת")
    
    lead = Lead(
        domain=data.domain,
        site_name=data.site_name,
        category=data.category,
        contact_info=data.contact_info,
        seo_data=data.seo_data,
        source_url=data.source_url,
        status="new"
    )
    
    session.add(lead)
    await session.flush()
    await session.refresh(lead)
    
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: int,
    data: LeadUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון ליד קיים
    """
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    # עדכון שדות
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)
    
    await session.flush()
    await session.refresh(lead)
    
    return lead


@router.delete("/{lead_id}")
async def delete_lead(
    lead_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת ליד
    """
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    await session.delete(lead)
    
    return {"message": f"ליד {lead_id} נמחק בהצלחה"}


@router.post("/{lead_id}/status")
async def update_lead_status(
    lead_id: int,
    status: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון סטטוס ליד
    """
    valid_statuses = ["new", "scanned", "matched", "contacted", "responded", "installed", "rejected"]
    
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"סטטוס לא תקין. אפשרויות: {', '.join(valid_statuses)}"
        )
    
    result = await session.execute(
        select(Lead).where(Lead.id == lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="ליד לא נמצא")
    
    lead.status = status
    if status == "contacted":
        lead.last_contacted_at = datetime.utcnow()
    
    await session.flush()
    
    return {"message": f"סטטוס עודכן ל-{status}", "lead_id": lead_id}


@router.post("/import-from-scan")
async def import_leads_from_scan(
    require_calc: bool = True,
    require_email: bool = True,
    only_kept: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """
    ייבוא לידים מתור הסריקה
    
    ממיר אתרים מ-scan_queue ללידים לפי הקריטריונים:
    - require_calc: רק אתרים עם מחשבון מותאם
    - require_email: רק אתרים עם מייל
    - only_kept: רק אתרים שלא חסומים (lead_site / small_business)
    """
    from sqlalchemy import text
    
    # שליפת אתרים מתור הסריקה שעומדים בקריטריונים
    query = """
        SELECT 
            sq.domain,
            sq.owner_email,
            sq.owner_phone,
            sq.owner_org,
            sq.business_type,
            sq.gpt_recommended_calc_id,
            sq.recommended_calc_id,
            sq.gpt_recommended_calc_reason,
            sq.url
        FROM scan_queue sq
        LEFT JOIN leads l ON sq.domain = l.domain
        WHERE l.id IS NULL
    """
    
    conditions = []
    if require_calc:
        conditions.append("(sq.gpt_recommended_calc_id IS NOT NULL OR sq.recommended_calc_id IS NOT NULL)")
    if require_email:
        conditions.append("sq.owner_email IS NOT NULL AND sq.owner_email != ''")
    if only_kept:
        # Only import domains that are NOT blacklisted (lead_site, small_business, or unknown/not-yet-classified)
        conditions.append("(sq.is_blacklisted = 0 OR sq.is_blacklisted IS NULL)")
        conditions.append("(sq.business_type IN ('lead_site', 'small_business') OR sq.business_type IS NULL)")
    
    if conditions:
        query += " AND " + " AND ".join(conditions)
    
    result = await session.execute(text(query))
    rows = result.fetchall()
    
    created = 0
    skipped = 0
    
    for row in rows:
        domain = row[0]
        owner_email = row[1]
        owner_phone = row[2]
        owner_org = row[3]
        business_type = row[4]
        gpt_calc_id = row[5]
        calc_id = row[6]
        calc_reason = row[7]
        source_url = row[8]
        
        # בדיקה אם כבר קיים
        existing = await session.execute(
            select(Lead).where(Lead.domain == domain)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        # Check if business_type requires blacklisting
        BLOCK_CATEGORIES = [
            "bank", "insurance", "corporation", "fintech", "government",
            "academia", "hospital", "nonprofit", "news", "ecommerce_giant", "religious"
        ]
        lead_status = "blacklisted" if business_type in BLOCK_CATEGORIES else "matched"
        
        # יצירת ליד חדש
        lead = Lead(
            domain=domain,
            site_name=owner_org or domain,
            category=business_type,
            contact_info={
                "emails": [owner_email] if owner_email else [],
                "phones": [owner_phone] if owner_phone else [],
                "name": owner_org
            },
            ai_status={
                "calc_reason": calc_reason,
                "is_real": True
            },
            status=lead_status,
            recommended_calc_id=gpt_calc_id or calc_id,
            source_url=source_url
        )
        
        session.add(lead)
        created += 1
    
    await session.commit()
    
    return {
        "status": "success",
        "created": created,
        "skipped": skipped,
        "message": f"נוצרו {created} לידים חדשים"
    }