"""
PartnerCalc OS - Lead Hunter API
קליטת פוסטים מפייסבוק, ניהול לידים, קטגוריות וסטטיסטיקות
"""
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from loguru import logger

from app.database import get_async_session
from app.config import settings
from app.models.lead_hunter import LeadCategory, LeadActor, LeadPost, AIFeedback, LeadArea, VALID_AREAS
from app.services.lead_hunter_service import process_ingest, classify_and_notify_background

router = APIRouter()

INGEST_TOKEN = "lead-hunter-secret-2024"


# ============================================================
#  Schemas
# ============================================================

class IngestPostRequest(BaseModel):
    url: str
    description: str
    posted_at: Optional[str] = None
    group_name: Optional[str] = None
    group_url: Optional[str] = None
    actor_name: Optional[str] = None
    actor_url: Optional[str] = None


class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    classification_prompt: str
    reply_prompt: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    whatsapp_name: Optional[str] = None
    is_alert_worthy: bool = True


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    classification_prompt: Optional[str] = None
    reply_prompt: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    whatsapp_name: Optional[str] = None
    is_alert_worthy: Optional[bool] = None
    is_active: Optional[bool] = None


class PostStatusUpdate(BaseModel):
    status: Optional[str] = None
    category_id: Optional[int] = None
    whatsapp_replied: Optional[bool] = None
    note: Optional[str] = None  # לפידבק


class RegenerateReplyRequest(BaseModel):
    pass


class AreaUpdate(BaseModel):
    is_reply_enabled: Optional[bool] = None
    is_whatsapp_enabled: Optional[bool] = None
    is_visible: Optional[bool] = None


# ============================================================
#  Ingest Endpoint (נקרא מ-Google Apps Script)
# ============================================================

@router.post("/ingest")
async def ingest_post(
    payload: IngestPostRequest,
    background_tasks: BackgroundTasks,
    x_ingest_token: Optional[str] = Header(None),
    skip_notify: bool = Query(False, description="Skip WhatsApp notification (for bulk import)"),
    session: AsyncSession = Depends(get_async_session),
):
    """
    קליטת פוסט חדש מגיליון Google Sheets.
    נדרש Header: X-Ingest-Token
    """
    if x_ingest_token != INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized - invalid token")

    if not payload.url or not payload.description:
        raise HTTPException(status_code=422, detail="url and description are required")

    # Parse posted_at
    posted_at = None
    if payload.posted_at:
        try:
            posted_at = datetime.fromisoformat(payload.posted_at.replace("Z", "+00:00").split(".")[0])
        except Exception:
            pass

    result = await process_ingest(
        post_url=payload.url,
        description=payload.description,
        posted_at=posted_at,
        group_name=payload.group_name or "",
        group_url=payload.group_url or "",
        actor_name=payload.actor_name or "לא ידוע",
        actor_url=payload.actor_url or payload.url,
        session=session,
        skip_notify=skip_notify,
    )

    # AI classification runs in background - returns immediately
    if result["status"] == "created":
        background_tasks.add_task(
            classify_and_notify_background,
            post_id=result["post_id"],
            actor_id=result["actor_id"],
            description=payload.description,
            actor_name=payload.actor_name or "לא ידוע",
            group_name=payload.group_name or "",
            skip_notify=skip_notify,
        )

    return result


# ============================================================
#  Posts
# ============================================================

@router.get("/posts")
async def get_posts(
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    area: Optional[str] = Query(None),
    whatsapp_sent: Optional[bool] = Query(None),
    whatsapp_replied: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    session: AsyncSession = Depends(get_async_session),
):
    """רשימת פוסטים עם פילטרים"""
    q = (
        select(LeadPost, LeadActor, LeadCategory)
        .outerjoin(LeadActor, LeadPost.actor_id == LeadActor.id)
        .outerjoin(LeadCategory, LeadPost.category_id == LeadCategory.id)
        .order_by(desc(LeadPost.created_at))
    )

    if status:
        q = q.where(LeadPost.status == status)
    if category_id is not None:
        q = q.where(LeadPost.category_id == category_id)
    if area is not None:
        q = q.where(LeadPost.area == area)
    if whatsapp_sent is not None:
        q = q.where(LeadPost.whatsapp_sent == whatsapp_sent)
    if whatsapp_replied is not None:
        q = q.where(LeadPost.whatsapp_replied == whatsapp_replied)

    # Count total
    count_q = select(func.count()).select_from(LeadPost)
    if status:
        count_q = count_q.where(LeadPost.status == status)
    if category_id is not None:
        count_q = count_q.where(LeadPost.category_id == category_id)
    if area is not None:
        count_q = count_q.where(LeadPost.area == area)

    total_result = await session.execute(count_q)
    total = total_result.scalar()

    result = await session.execute(q.offset(offset).limit(limit))
    rows = result.all()

    posts = []
    for row in rows:
        post, actor, category = row
        posts.append({
            "id": post.id,
            "post_url": post.post_url,
            "description": post.description,
            "posted_at": post.posted_at.isoformat() if post.posted_at else None,
            "group_name": post.group_name,
            "group_url": post.group_url,
            "area": post.area,
            "status": post.status,
            "ai_reply": post.ai_reply,
            "ai_confidence": post.ai_confidence,
            "ai_reasoning": post.ai_reasoning,
            "whatsapp_sent": post.whatsapp_sent,
            "whatsapp_sent_at": post.whatsapp_sent_at.isoformat() if post.whatsapp_sent_at else None,
            "whatsapp_replied": post.whatsapp_replied,
            "whatsapp_replied_at": post.whatsapp_replied_at.isoformat() if post.whatsapp_replied_at else None,
            "created_at": post.created_at.isoformat() if post.created_at else None,
            "actor": {
                "id": actor.id,
                "name": actor.actor_name,
                "url": actor.actor_url,
                "post_count": actor.post_count,
            } if actor else None,
            "category": {
                "id": category.id,
                "name": category.name,
                "is_alert_worthy": category.is_alert_worthy,
            } if category else None,
        })

    return {"posts": posts, "total": total, "offset": offset, "limit": limit}


@router.get("/posts/{post_id}")
async def get_post(post_id: int, session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(select(LeadPost).where(LeadPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    actor_result = await session.execute(select(LeadActor).where(LeadActor.id == post.actor_id))
    actor = actor_result.scalar_one_or_none()

    category_result = await session.execute(select(LeadCategory).where(LeadCategory.id == post.category_id))
    category = category_result.scalar_one_or_none()

    return {
        "id": post.id,
        "post_url": post.post_url,
        "description": post.description,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "group_name": post.group_name,
        "group_url": post.group_url,
        "area": post.area,
        "status": post.status,
        "ai_reply": post.ai_reply,
        "ai_confidence": post.ai_confidence,
        "ai_reasoning": post.ai_reasoning,
        "whatsapp_sent": post.whatsapp_sent,
        "whatsapp_sent_at": post.whatsapp_sent_at.isoformat() if post.whatsapp_sent_at else None,
        "whatsapp_replied": post.whatsapp_replied,
        "whatsapp_replied_at": post.whatsapp_replied_at.isoformat() if post.whatsapp_replied_at else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "actor": {
            "id": actor.id,
            "name": actor.actor_name,
            "url": actor.actor_url,
            "post_count": actor.post_count,
        } if actor else None,
        "category": {
            "id": category.id,
            "name": category.name,
        } if category else None,
    }


@router.put("/posts/{post_id}")
async def update_post(
    post_id: int,
    payload: PostStatusUpdate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    """עדכון סטטוס / קטגוריה / סימון תגובה"""
    result = await session.execute(select(LeadPost).where(LeadPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    old_category_id = post.category_id
    category_changed = False

    if payload.status is not None:
        post.status = payload.status

    if payload.whatsapp_replied is not None:
        post.whatsapp_replied = payload.whatsapp_replied
        if payload.whatsapp_replied:
            post.whatsapp_replied_at = datetime.utcnow()
            if post.status == "notified":
                post.status = "replied"

    # תיקון קטגוריה ידני → שמור feedback + ייצור תגובה חדשה
    if payload.category_id is not None and payload.category_id != old_category_id:
        feedback = AIFeedback(
            post_id=post.id,
            original_category_id=old_category_id,
            corrected_category_id=payload.category_id,
            is_irrelevant=False,
            note=payload.note,
        )
        session.add(feedback)
        post.category_id = payload.category_id
        post.status = "classified"
        category_changed = True

    await session.commit()

    if category_changed:
        background_tasks.add_task(
            _generate_reply_after_category_change, post_id, payload.category_id
        )

    return {"success": True, "post_id": post.id, "status": post.status}


async def _generate_reply_after_category_change(post_id: int, new_category_id: int):
    """Background: ייצור תגובה אוטומטית אחרי שינוי קטגוריה ידני"""
    from app.services.lead_hunter_service import generate_reply_with_ai
    from app.database import AsyncSessionLocal as async_session_factory

    try:
        async with async_session_factory() as session:
            post = (await session.execute(
                select(LeadPost).where(LeadPost.id == post_id)
            )).scalar_one_or_none()
            if not post:
                return

            category = (await session.execute(
                select(LeadCategory).where(LeadCategory.id == new_category_id)
            )).scalar_one_or_none()
            if not category or not category.reply_prompt:
                return

            actor = (await session.execute(
                select(LeadActor).where(LeadActor.id == post.actor_id)
            )).scalar_one_or_none()
            actor_name = actor.actor_name if actor else ""

            new_reply = await generate_reply_with_ai(post.description, category, actor_name)
            post.ai_reply = new_reply
            await session.commit()
            logger.info(f"Auto-generated reply for post {post_id} after category change")
    except Exception as e:
        logger.error(f"Failed to generate reply for post {post_id}: {e}")


@router.post("/posts/{post_id}/ignore")
async def ignore_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """סימון פוסט כ'לא רלוונטי' + שמירת feedback"""
    result = await session.execute(select(LeadPost).where(LeadPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    feedback = AIFeedback(
        post_id=post.id,
        original_category_id=post.category_id,
        corrected_category_id=None,
        is_irrelevant=True,
    )
    session.add(feedback)
    post.status = "ignored"

    await session.commit()
    return {"success": True}


@router.post("/posts/{post_id}/regenerate-reply")
async def regenerate_reply(
    post_id: int,
    session: AsyncSession = Depends(get_async_session),
):
    """הפעלה מחדש של AI לייצור תגובה"""
    from app.services.lead_hunter_service import generate_reply_with_ai

    result = await session.execute(select(LeadPost).where(LeadPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not post.category_id:
        raise HTTPException(status_code=400, detail="Post has no category assigned")

    cat_result = await session.execute(select(LeadCategory).where(LeadCategory.id == post.category_id))
    category = cat_result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    actor_result = await session.execute(select(LeadActor).where(LeadActor.id == post.actor_id))
    actor = actor_result.scalar_one_or_none()
    actor_name = actor.actor_name if actor else "לא ידוע"

    new_reply = await generate_reply_with_ai(post.description, category, actor_name)
    post.ai_reply = new_reply

    await session.commit()
    return {"success": True, "ai_reply": new_reply}


# ============================================================
#  Categories
# ============================================================

@router.get("/categories")
async def get_categories(session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(LeadCategory).order_by(LeadCategory.id)
    )
    categories = result.scalars().all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "classification_prompt": c.classification_prompt,
            "reply_prompt": c.reply_prompt,
            "whatsapp_phone": c.whatsapp_phone,
            "whatsapp_name": c.whatsapp_name,
            "is_alert_worthy": c.is_alert_worthy,
            "auto_reply_enabled": c.auto_reply_enabled,
            "is_active": c.is_active,
        }
        for c in categories
    ]


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(LeadCategory).where(LeadCategory.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(category, field, value)

    await session.commit()
    return {"success": True}


# ============================================================
#  Areas
# ============================================================

@router.get("/areas")
async def get_areas(session: AsyncSession = Depends(get_async_session)):
    """רשימת אזורים גיאוגרפיים עם הגדרותיהם"""
    result = await session.execute(select(LeadArea).order_by(LeadArea.id))
    areas = result.scalars().all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "is_reply_enabled": a.is_reply_enabled,
            "is_whatsapp_enabled": a.is_whatsapp_enabled,
            "is_visible": a.is_visible,
        }
        for a in areas
    ]


@router.put("/areas/{area_id}")
async def update_area(
    area_id: int,
    payload: AreaUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """עדכון הגדרות אזור"""
    result = await session.execute(select(LeadArea).where(LeadArea.id == area_id))
    area = result.scalar_one_or_none()
    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(area, field, value)

    await session.commit()
    return {"success": True}


# ============================================================
#  Statistics
# ============================================================

@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_async_session)):
    """סטטיסטיקות ראשיות לדשבורד"""

    total = (await session.execute(select(func.count()).select_from(LeadPost))).scalar()
    notified = (await session.execute(
        select(func.count()).select_from(LeadPost).where(LeadPost.whatsapp_sent == True)
    )).scalar()
    replied = (await session.execute(
        select(func.count()).select_from(LeadPost).where(LeadPost.whatsapp_replied == True)
    )).scalar()
    pending = (await session.execute(
        select(func.count()).select_from(LeadPost).where(LeadPost.status == "new")
    )).scalar()
    ignored = (await session.execute(
        select(func.count()).select_from(LeadPost).where(LeadPost.status == "ignored")
    )).scalar()

    # לפי קטגוריה
    by_cat_result = await session.execute(
        select(LeadCategory.name, func.count(LeadPost.id).label("count"))
        .outerjoin(LeadPost, LeadPost.category_id == LeadCategory.id)
        .group_by(LeadCategory.id, LeadCategory.name)
        .order_by(LeadCategory.id)
    )
    by_category = [{"name": row.name, "count": row.count} for row in by_cat_result]

    return {
        "total": total,
        "notified": notified,
        "replied": replied,
        "pending_classification": pending,
        "ignored": ignored,
        "reply_rate": round((replied / notified * 100) if notified else 0, 1),
        "by_category": by_category,
    }
