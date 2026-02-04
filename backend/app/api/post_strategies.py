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
