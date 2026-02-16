"""
PartnerCalc OS - Post Strategies API
API endpoints לניהול אסטרטגיות כתיבה לפוסטים
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_async_session
from app.models.post_strategy import PostStrategy

router = APIRouter()


# ========== Schemas ==========

class StrategyCreate(BaseModel):
    name: str
    slug: str
    icon: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    post_template: Optional[str] = None
    example_post: Optional[str] = None
    sort_order: int = 0


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    post_template: Optional[str] = None
    example_post: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    slug: str
    icon: Optional[str]
    description: Optional[str]
    system_prompt: Optional[str]
    post_template: Optional[str]
    example_post: Optional[str]
    is_active: bool
    sort_order: int
    times_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class PreviewRequest(BaseModel):
    calculator_name: str
    calculator_url: str


class PreviewResponse(BaseModel):
    preview_text: str
    strategy_name: str


# ========== Endpoints ==========

@router.get("", response_model=List[StrategyResponse])
async def get_strategies(
    active_only: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת רשימת אסטרטגיות"""
    query = select(PostStrategy).order_by(PostStrategy.sort_order)
    
    if active_only:
        query = query.where(PostStrategy.is_active == True)
    
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת אסטרטגיה לפי ID"""
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return strategy


@router.post("", response_model=StrategyResponse)
async def create_strategy(
    data: StrategyCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת אסטרטגיה חדשה"""
    # בדיקת slug ייחודי
    existing = await session.execute(
        select(PostStrategy).where(PostStrategy.slug == data.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    strategy = PostStrategy(**data.model_dump())
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון אסטרטגיה"""
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # בדיקת slug ייחודי אם משתנה
    if data.slug and data.slug != strategy.slug:
        existing = await session.execute(
            select(PostStrategy).where(PostStrategy.slug == data.slug)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already exists")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(strategy, key, value)
    
    await session.commit()
    await session.refresh(strategy)
    
    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """מחיקת אסטרטגיה (soft delete)"""
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy.is_active = False
    await session.commit()
    
    return {"message": "Strategy deactivated", "id": strategy_id}


@router.post("/{strategy_id}/preview", response_model=PreviewResponse)
async def preview_strategy(
    strategy_id: int,
    data: PreviewRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """תצוגה מקדימה של פוסט עם האסטרטגיה"""
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if not strategy.post_template:
        raise HTTPException(status_code=400, detail="Strategy has no template")
    
    # החלפת משתנים
    preview_text = strategy.post_template.format(
        calculator_name=data.calculator_name,
        calculator_url=data.calculator_url
    )
    
    return PreviewResponse(
        preview_text=preview_text,
        strategy_name=strategy.name
    )


@router.post("/{strategy_id}/increment-usage")
async def increment_usage(
    strategy_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון מונה שימוש"""
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy.times_used = (strategy.times_used or 0) + 1
    await session.commit()
    
    return {"times_used": strategy.times_used}


class DebugPromptRequest(BaseModel):
    calculator_name: str = "מחשבון משכנתא"
    calculator_url: str = "https://loan-israel.co.il/mashkanta/"
    calculator_summary: str = "מחשבון משכנתא חכם לחישוב החזר חודשי"
    group_name: str = "נדל\"ן ומשכנתאות ישראל"


class DebugPromptResponse(BaseModel):
    strategy_name: str
    system_prompt: str
    user_prompt: str
    post_template: Optional[str]
    will_use_template: bool
    final_output_preview: Optional[str]


@router.post("/{strategy_id}/debug-prompt", response_model=DebugPromptResponse)
async def debug_strategy_prompt(
    strategy_id: int,
    data: DebugPromptRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    🔍 DEBUG: הצגת הפרומפטים המלאים שנשלחים ל-AI
    
    משמש לבדיקה ואיתור בעיות ביצירת פוסטים
    """
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # בניית הפרומפט המלא שנשלח ל-AI
    system_prompt = strategy.system_prompt or "אתה כותב פוסטים אישיים ומושכים לפייסבוק."
    
    user_prompt = f"""
צור פוסט לקבוצת פייסבוק "{data.group_name}" עבור המחשבון:

שם המחשבון: {data.calculator_name}
קישור: {data.calculator_url}
תיאור: {data.calculator_summary}

הנחיות האסטרטגיה:
{strategy.system_prompt or "אין הנחיות ספציפיות"}

פוסטים קודמים (להימנע מחזרות):
אין

הנחיות:
- כתוב בגוף ראשון, טון אישי
- 4-7 שורות
- 2-3 אימוג'ים
- קריאה לפעולה ברורה

החזר רק את טקסט הפוסט.
"""
    
    # בדיקה אם נשתמש בתבנית או ב-AI
    will_use_template = bool(strategy.post_template)
    final_output_preview = None
    
    if will_use_template and strategy.post_template:
        try:
            final_output_preview = strategy.post_template.format(
                calculator_name=data.calculator_name,
                calculator_url=data.calculator_url
            )
        except KeyError as e:
            final_output_preview = f"⚠️ שגיאה בתבנית: חסר משתנה {e}"
    
    return DebugPromptResponse(
        strategy_name=strategy.name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        post_template=strategy.post_template,
        will_use_template=will_use_template,
        final_output_preview=final_output_preview
    )


@router.post("/{strategy_id}/generate-with-ai")
async def generate_with_ai(
    strategy_id: int,
    data: DebugPromptRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    🤖 יצירת פוסט אמיתי עם AI (לא משתמש בתבנית)
    
    מאלץ שימוש ב-AI גם אם יש תבנית
    """
    from app.services.post_generator_service import get_post_generator_service
    
    result = await session.execute(
        select(PostStrategy).where(PostStrategy.id == strategy_id)
    )
    strategy = result.scalar_one_or_none()
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    generator = get_post_generator_service()
    
    # יצירה עם AI - ללא תבנית!
    gen_result = await generator.generate_strategic_post(
        calculator_name=data.calculator_name,
        calculator_url=data.calculator_url,
        calculator_summary=data.calculator_summary,
        strategy_system_prompt=strategy.system_prompt or "",
        strategy_post_template="",  # מאלצים AI, לא תבנית!
        group_name=data.group_name,
        previous_posts=[],
        include_first_comment=False
    )
    
    # עדכון מונה
    strategy.times_used = (strategy.times_used or 0) + 1
    await session.commit()
    
    return {
        "strategy_name": strategy.name,
        "generated_content": gen_result.get("post_content"),
        "error": gen_result.get("error"),
        "used_ai": True,
        # 🐞 DEBUG: הפרומפטים המלאים שנשלחו ל-AI
        "debug_full_prompt": gen_result.get("debug_full_prompt"),
        "debug_system_message": gen_result.get("debug_system_message")
    }
