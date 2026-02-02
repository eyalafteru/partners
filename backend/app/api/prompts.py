"""
PartnerCalc OS - Prompts API
ניהול פרומפטים לצמתי AI
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_async_session
from app.models.prompt import Prompt, AILog

router = APIRouter()


# ========== Pydantic Schemas ==========

class PromptCreate(BaseModel):
    """סכמה ליצירת פרומפט"""
    node_name: str
    display_name: str
    description: Optional[str] = None
    system_prompt: str
    user_prompt_template: str
    available_variables: List[str]
    model_name: str = "dictalm-atomic-v2-q4"
    temperature: float = 0.7
    max_tokens: int = 500


class PromptUpdate(BaseModel):
    """סכמה לעדכון פרומפט"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    user_prompt_template: Optional[str] = None
    available_variables: Optional[List[str]] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    is_active: Optional[bool] = None


class PromptResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    node_name: str
    display_name: Optional[str]
    description: Optional[str]
    system_prompt: Optional[str]
    user_prompt_template: Optional[str]
    available_variables: Optional[List[str]]
    model_name: str
    temperature: float
    max_tokens: int
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class PromptTestRequest(BaseModel):
    """סכמה לבדיקת פרומפט"""
    variables: dict  # {"domain": "example.com", "inner_text": "..."}


class AILogResponse(BaseModel):
    """סכמה ללוג AI"""
    id: int
    prompt_id: int
    lead_id: Optional[int]
    input_data: Optional[dict]
    response: Optional[str]
    execution_time_ms: Optional[int]
    success: bool
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ========== API Endpoints ==========

@router.get("/", response_model=List[PromptResponse])
async def list_prompts(
    active_only: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת כל הפרומפטים
    """
    query = select(Prompt)
    
    if active_only:
        query = query.where(Prompt.is_active == True)
    
    query = query.order_by(Prompt.id)
    result = await session.execute(query)
    
    return result.scalars().all()


@router.get("/nodes")
async def list_node_names(
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת שמות צמתים
    """
    result = await session.execute(
        select(Prompt.node_name, Prompt.display_name, Prompt.is_active)
        .order_by(Prompt.id)
    )
    
    return [
        {"node_name": row[0], "display_name": row[1], "is_active": row[2]}
        for row in result.all()
    ]


@router.get("/{node_name}", response_model=PromptResponse)
async def get_prompt(
    node_name: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת פרומפט לפי שם הצומת
    """
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    return prompt


@router.get("/{node_name}/stats")
async def get_prompt_stats(
    node_name: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות של פרומפט
    """
    # קבלת הפרומפט
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    # סטטיסטיקות
    result = await session.execute(
        select(func.count(AILog.id))
        .where(AILog.prompt_id == prompt.id)
    )
    total_calls = result.scalar()
    
    result = await session.execute(
        select(func.count(AILog.id))
        .where(AILog.prompt_id == prompt.id, AILog.success == True)
    )
    success_calls = result.scalar()
    
    result = await session.execute(
        select(func.avg(AILog.execution_time_ms))
        .where(AILog.prompt_id == prompt.id)
    )
    avg_time = result.scalar()
    
    return {
        "node_name": node_name,
        "total_calls": total_calls,
        "success_calls": success_calls,
        "success_rate": (success_calls / total_calls * 100) if total_calls > 0 else 0,
        "avg_execution_time_ms": round(avg_time) if avg_time else 0
    }


@router.get("/{node_name}/logs", response_model=List[AILogResponse])
async def get_prompt_logs(
    node_name: str,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_async_session)
):
    """
    היסטוריית קריאות לפרומפט
    """
    # קבלת הפרומפט
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    # קבלת לוגים
    result = await session.execute(
        select(AILog)
        .where(AILog.prompt_id == prompt.id)
        .order_by(AILog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all()


@router.post("/", response_model=PromptResponse)
async def create_prompt(
    data: PromptCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת פרומפט חדש
    """
    # בדיקה שהשם לא קיים
    existing = await session.execute(
        select(Prompt).where(Prompt.node_name == data.node_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="פרומפט עם שם זה כבר קיים")
    
    prompt = Prompt(
        node_name=data.node_name,
        display_name=data.display_name,
        description=data.description,
        system_prompt=data.system_prompt,
        user_prompt_template=data.user_prompt_template,
        available_variables=data.available_variables,
        model_name=data.model_name,
        temperature=data.temperature,
        max_tokens=data.max_tokens,
        is_active=True
    )
    
    session.add(prompt)
    await session.flush()
    await session.refresh(prompt)
    
    return prompt


@router.put("/{node_name}", response_model=PromptResponse)
async def update_prompt(
    node_name: str,
    data: PromptUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון פרומפט קיים
    """
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    # עדכון שדות
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prompt, field, value)
    
    await session.flush()
    await session.refresh(prompt)
    
    return prompt


@router.post("/{node_name}/test")
async def test_prompt(
    node_name: str,
    data: PromptTestRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    בדיקת פרומפט עם משתנים
    """
    # קבלת הפרומפט
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    # החלפת משתנים
    user_prompt = prompt.user_prompt_template
    for key, value in data.variables.items():
        user_prompt = user_prompt.replace(f"{{{{{key}}}}}", str(value))
    
    # TODO: קריאה ל-Ollama
    # from app.ai.ollama_client import OllamaClient
    # client = OllamaClient()
    # response = await client.generate(prompt.system_prompt, user_prompt, prompt.model_name)
    
    return {
        "node_name": node_name,
        "full_prompt": user_prompt,
        "response": "// TODO: הרצת Ollama //",
        "variables_used": data.variables
    }


@router.delete("/{node_name}")
async def delete_prompt(
    node_name: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת פרומפט
    """
    result = await session.execute(
        select(Prompt).where(Prompt.node_name == node_name)
    )
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        raise HTTPException(status_code=404, detail="פרומפט לא נמצא")
    
    await session.delete(prompt)
    
    return {"message": f"פרומפט {node_name} נמחק בהצלחה"}
