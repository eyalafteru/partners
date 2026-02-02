"""
PartnerCalc OS - Email Templates API
CRUD לתבניות מייל
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_async_session
from app.models.email_template import EmailTemplate

router = APIRouter()


# ========== Pydantic Schemas ==========

class TemplateCreate(BaseModel):
    """סכמה ליצירת תבנית"""
    name: str
    subject: str
    body_text: str
    body_html: Optional[str] = None
    category: str = "first_contact"
    variables: List[str] = []


class TemplateUpdate(BaseModel):
    """סכמה לעדכון תבנית"""
    name: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    variables: Optional[List[str]] = None


class TemplateResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    name: str
    subject: str
    body_text: str
    body_html: Optional[str]
    category: str
    is_active: bool
    variables: List[str]
    usage_count: int
    open_rate: float
    click_rate: float
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class TemplatePreviewRequest(BaseModel):
    """סכמה לתצוגה מקדימה"""
    variables: dict = {}


class TemplatePreviewResponse(BaseModel):
    """תגובת תצוגה מקדימה"""
    subject: str
    body_text: str
    body_html: Optional[str]


# ========== API Endpoints ==========

@router.get("/", response_model=List[TemplateResponse])
async def list_templates(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת תבניות
    """
    query = select(EmailTemplate)
    
    if category:
        query = query.where(EmailTemplate.category == category)
    if is_active is not None:
        query = query.where(EmailTemplate.is_active == is_active)
    
    query = query.order_by(EmailTemplate.created_at.desc())
    result = await session.execute(query)
    templates = result.scalars().all()
    
    # Convert variables from JSON to list
    response = []
    for t in templates:
        template_dict = {
            "id": t.id,
            "name": t.name,
            "subject": t.subject,
            "body_text": t.body_text,
            "body_html": t.body_html,
            "category": t.category,
            "is_active": t.is_active,
            "variables": t.variables if isinstance(t.variables, list) else [],
            "usage_count": t.usage_count or 0,
            "open_rate": t.open_rate or 0.0,
            "click_rate": t.click_rate or 0.0,
            "created_at": t.created_at,
            "updated_at": t.updated_at
        }
        response.append(TemplateResponse(**template_dict))
    
    return response


@router.get("/categories")
async def list_categories():
    """
    קבלת רשימת קטגוריות
    """
    return [
        {"id": "first_contact", "name": "פנייה ראשונה", "icon": "📧"},
        {"id": "follow_up", "name": "מעקב", "icon": "🔄"},
        {"id": "response", "name": "תשובה", "icon": "↩️"},
        {"id": "reminder", "name": "תזכורת", "icon": "⏰"},
        {"id": "closing", "name": "סגירה", "icon": "✅"}
    ]


@router.get("/variables")
async def list_available_variables():
    """
    קבלת רשימת משתנים זמינים
    """
    return {
        "lead": [
            {"key": "domain", "label": "דומיין", "example": "example.co.il"},
            {"key": "site_name", "label": "שם האתר", "example": "כלכליסט"},
            {"key": "site_url", "label": "כתובת האתר", "example": "https://example.co.il"},
            {"key": "category", "label": "קטגוריה", "example": "פיננסים"},
        ],
        "contact": [
            {"key": "contact_name", "label": "שם איש קשר", "example": "יוסי כהן"},
            {"key": "contact_first_name", "label": "שם פרטי", "example": "יוסי"},
            {"key": "contact_email", "label": "מייל איש קשר", "example": "yossi@example.com"},
            {"key": "contact_phone", "label": "טלפון איש קשר", "example": "050-1234567"},
            {"key": "contact_company", "label": "שם החברה", "example": "כלכליסט בע\"מ"},
        ],
        "calculator": [
            {"key": "calculator_name", "label": "שם המחשבון", "example": "מחשבון משכנתא"},
            {"key": "calculator_description", "label": "תיאור המחשבון", "example": "מחשבון לחישוב החזר משכנתא"},
            {"key": "calculator_benefit", "label": "יתרון עסקי", "example": "מגדיל המרות ב-30%"},
            {"key": "calculator_demo_url", "label": "לינק להדגמה", "example": "https://demo.calc.com"},
            {"key": "match_score", "label": "ציון התאמה", "example": "92%"},
            {"key": "match_reason", "label": "סיבת התאמה", "example": "אתר עוסק במשכנתאות"},
        ],
        "date": [
            {"key": "today", "label": "היום (עברית)", "example": "23 בינואר 2026"},
            {"key": "today_short", "label": "תאריך קצר", "example": "23/01/2026"},
            {"key": "current_month", "label": "חודש נוכחי", "example": "ינואר"},
            {"key": "current_year", "label": "שנה נוכחית", "example": "2026"},
            {"key": "day_of_week", "label": "יום בשבוע", "example": "שישי"},
        ],
        "sender": [
            {"key": "my_name", "label": "שם השולח", "example": "אייל"},
            {"key": "my_email", "label": "מייל השולח", "example": "eyal@company.com"},
            {"key": "my_phone", "label": "טלפון השולח", "example": "050-1234567"},
            {"key": "my_company", "label": "שם החברה", "example": "הלוואות ישראל"},
            {"key": "my_title", "label": "תפקיד", "example": "מנהל שותפויות"},
            {"key": "my_signature", "label": "חתימה", "example": "אייל | הלוואות ישראל"},
        ]
    }


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת תבנית לפי ID
    """
    result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        subject=template.subject,
        body_text=template.body_text,
        body_html=template.body_html,
        category=template.category,
        is_active=template.is_active,
        variables=template.variables if isinstance(template.variables, list) else [],
        usage_count=template.usage_count or 0,
        open_rate=template.open_rate or 0.0,
        click_rate=template.click_rate or 0.0,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.post("/", response_model=TemplateResponse)
async def create_template(
    data: TemplateCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת תבנית חדשה
    """
    # Extract variables from template content
    import re
    found_vars = set()
    for text in [data.subject, data.body_text, data.body_html or ""]:
        matches = re.findall(r'\{\{(\w+)\}\}', text)
        found_vars.update(matches)
    
    template = EmailTemplate(
        name=data.name,
        subject=data.subject,
        body_text=data.body_text,
        body_html=data.body_html,
        category=data.category,
        variables=list(found_vars) if found_vars else data.variables
    )
    
    session.add(template)
    await session.commit()
    await session.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        subject=template.subject,
        body_text=template.body_text,
        body_html=template.body_html,
        category=template.category,
        is_active=template.is_active,
        variables=template.variables if isinstance(template.variables, list) else [],
        usage_count=0,
        open_rate=0.0,
        click_rate=0.0,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    data: TemplateUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון תבנית
    """
    result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    
    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)
    
    # Re-extract variables if content changed
    import re
    if any(f in update_data for f in ["subject", "body_text", "body_html"]):
        found_vars = set()
        for text in [template.subject, template.body_text, template.body_html or ""]:
            matches = re.findall(r'\{\{(\w+)\}\}', text)
            found_vars.update(matches)
        template.variables = list(found_vars)
    
    await session.commit()
    await session.refresh(template)
    
    return TemplateResponse(
        id=template.id,
        name=template.name,
        subject=template.subject,
        body_text=template.body_text,
        body_html=template.body_html,
        category=template.category,
        is_active=template.is_active,
        variables=template.variables if isinstance(template.variables, list) else [],
        usage_count=template.usage_count or 0,
        open_rate=template.open_rate or 0.0,
        click_rate=template.click_rate or 0.0,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת תבנית
    """
    result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    
    await session.delete(template)
    await session.commit()
    
    return {"message": f"תבנית '{template.name}' נמחקה"}


@router.post("/{template_id}/preview", response_model=TemplatePreviewResponse)
async def preview_template(
    template_id: int,
    data: TemplatePreviewRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    תצוגה מקדימה של תבנית עם משתנים
    """
    from app.services.template_engine import render_template
    
    result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    
    # Add sample data if not provided
    sample_data = {
        "domain": "example.co.il",
        "site_name": "דוגמה",
        "site_url": "https://example.co.il",
        "category": "פיננסים",
        "contact_name": "יוסי כהן",
        "contact_first_name": "יוסי",
        "contact_email": "yossi@example.com",
        "contact_phone": "050-1234567",
        "contact_company": "חברה לדוגמה בע\"מ",
        "calculator_name": "מחשבון משכנתא",
        "calculator_description": "מחשבון לחישוב החזר משכנתא",
        "calculator_benefit": "מגדיל המרות ב-30%",
        "calculator_demo_url": "https://demo.partnercalc.com/mortgage",
        "match_score": "92%",
        "match_reason": "האתר עוסק במשכנתאות ופיננסים",
        "my_name": "אייל",
        "my_email": "eyal@company.com",
        "my_phone": "050-9876543",
        "my_company": "הלוואות ישראל",
        "my_title": "מנהל שותפויות",
        "my_signature": "אייל | הלוואות ישראל | 050-9876543",
        **data.variables  # Override with provided values
    }
    
    rendered_subject = render_template(template.subject, sample_data)
    rendered_body = render_template(template.body_text, sample_data)
    rendered_html = render_template(template.body_html, sample_data) if template.body_html else None
    
    return TemplatePreviewResponse(
        subject=rendered_subject,
        body_text=rendered_body,
        body_html=rendered_html
    )


@router.post("/{template_id}/duplicate", response_model=TemplateResponse)
async def duplicate_template(
    template_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    שכפול תבנית
    """
    result = await session.execute(
        select(EmailTemplate).where(EmailTemplate.id == template_id)
    )
    original = result.scalar_one_or_none()
    
    if not original:
        raise HTTPException(status_code=404, detail="תבנית לא נמצאה")
    
    # Create copy
    new_template = EmailTemplate(
        name=f"{original.name} (העתק)",
        subject=original.subject,
        body_text=original.body_text,
        body_html=original.body_html,
        category=original.category,
        variables=original.variables
    )
    
    session.add(new_template)
    await session.commit()
    await session.refresh(new_template)
    
    return TemplateResponse(
        id=new_template.id,
        name=new_template.name,
        subject=new_template.subject,
        body_text=new_template.body_text,
        body_html=new_template.body_html,
        category=new_template.category,
        is_active=new_template.is_active,
        variables=new_template.variables if isinstance(new_template.variables, list) else [],
        usage_count=0,
        open_rate=0.0,
        click_rate=0.0,
        created_at=new_template.created_at,
        updated_at=new_template.updated_at
    )
