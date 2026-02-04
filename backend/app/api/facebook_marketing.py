"""
PartnerCalc OS - Facebook Marketing API
API endpoints לניהול פרסום בקבוצות פייסבוק
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_async_session
from app.models.facebook_marketing import (
    FacebookGroup,
    FacebookCampaign,
    FacebookPost,
    FacebookReply,
    FacebookConversation,
    FacebookMessage,
    FacebookPostTemplate
)
from app.services.facebook_marketing_service import get_facebook_marketing_service

router = APIRouter()


# ========== Schemas ==========

class GroupCreate(BaseModel):
    fb_group_id: str
    name: str
    url: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    auto_reply_enabled: Optional[bool] = None

class GroupResponse(BaseModel):
    id: int
    fb_group_id: str
    name: str
    url: Optional[str]
    category: Optional[str]
    member_count: int
    is_active: bool
    total_posts: int
    total_replies_received: int
    last_post_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class CampaignCreate(BaseModel):
    name: str
    topic: str
    target_group_ids: List[int]
    target_audience: Optional[str] = None
    template_id: Optional[int] = None
    image_percentage: int = 50
    delay_between_posts: int = 60
    max_posts_per_day: int = 10

class CampaignResponse(BaseModel):
    id: int
    name: str
    topic: str
    target_audience: Optional[str]
    status: str
    image_percentage: int
    total_posts_generated: int
    total_posts_approved: int
    total_posts_published: int
    total_replies: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: int
    campaign_id: Optional[int]
    group_id: int
    content: str
    has_image: bool
    image_url: Optional[str]
    status: str
    rejection_reason: Optional[str]
    replies_count: int
    published_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    content: Optional[str] = None

class ReplyResponse(BaseModel):
    id: int
    post_id: int
    fb_user_name: Optional[str]
    fb_user_profile_url: Optional[str]
    message: str
    ai_detected_intent: Optional[str]
    wants_private: bool
    status: str
    suggested_response: Optional[str]
    suggested_channel: Optional[str]
    actual_response: Optional[str]
    received_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReplyResponseAction(BaseModel):
    response_text: Optional[str] = None
    channel: Optional[str] = None  # comment or messenger

class SearchGroupsRequest(BaseModel):
    search_query: str
    max_groups: int = 20
    category: Optional[str] = None

class TemplateCreate(BaseModel):
    name: str
    base_content: str
    description: Optional[str] = None
    variables: List[str] = []
    include_image: bool = True
    image_prompt_template: Optional[str] = None
    category: Optional[str] = None

class TemplateResponse(BaseModel):
    id: int
    name: str
    base_content: str
    description: Optional[str]
    variables: List[str]
    include_image: bool
    times_used: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== Groups Endpoints ==========

@router.get("/groups", response_model=List[GroupResponse], tags=["Groups"])
async def get_groups(
    active_only: bool = True,
    category: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת רשימת קבוצות"""
    service = get_facebook_marketing_service(session)
    groups = await service.get_groups(
        active_only=active_only,
        category=category,
        limit=limit
    )
    return groups

@router.post("/groups", response_model=GroupResponse, tags=["Groups"])
async def create_group(
    data: GroupCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """הוספת קבוצה חדשה"""
    service = get_facebook_marketing_service(session)
    group = await service.add_group(**data.model_dump())
    await session.commit()
    return group

@router.put("/groups/{group_id}", response_model=GroupResponse, tags=["Groups"])
async def update_group(
    group_id: int,
    data: GroupUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון קבוצה"""
    result = await session.execute(
        select(FacebookGroup).where(FacebookGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(group, key, value)
    
    await session.commit()
    await session.refresh(group)
    return group

@router.delete("/groups/{group_id}", tags=["Groups"])
async def delete_group(
    group_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """מחיקת קבוצה (soft delete)"""
    result = await session.execute(
        select(FacebookGroup).where(FacebookGroup.id == group_id)
    )
    group = result.scalar_one_or_none()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    group.is_active = False
    await session.commit()
    
    return {"message": "Group deactivated", "id": group_id}

@router.post("/groups/search", response_model=List[GroupResponse], tags=["Groups"])
async def search_groups(
    data: SearchGroupsRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """חיפוש קבוצות ב-Apify והוספה למערכת"""
    service = get_facebook_marketing_service(session)
    groups = await service.search_and_add_groups(
        search_query=data.search_query,
        max_groups=data.max_groups,
        category=data.category
    )
    await session.commit()
    return groups


# ========== Templates Endpoints ==========

@router.get("/templates", response_model=List[TemplateResponse], tags=["Templates"])
async def get_templates(
    active_only: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת תבניות פוסטים"""
    query = select(FacebookPostTemplate)
    if active_only:
        query = query.where(FacebookPostTemplate.is_active == True)
    
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/templates", response_model=TemplateResponse, tags=["Templates"])
async def create_template(
    data: TemplateCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת תבנית חדשה"""
    template = FacebookPostTemplate(**data.model_dump())
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


# ========== Campaigns Endpoints ==========

@router.get("/campaigns", response_model=List[CampaignResponse], tags=["Campaigns"])
async def get_campaigns(
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת רשימת קמפיינים"""
    query = select(FacebookCampaign).order_by(FacebookCampaign.created_at.desc())
    
    if status:
        query = query.where(FacebookCampaign.status == status)
    
    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

@router.post("/campaigns", response_model=CampaignResponse, tags=["Campaigns"])
async def create_campaign(
    data: CampaignCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת קמפיין חדש"""
    service = get_facebook_marketing_service(session)
    campaign = await service.create_campaign(**data.model_dump())
    await session.commit()
    return campaign

@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse, tags=["Campaigns"])
async def get_campaign(
    campaign_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת פרטי קמפיין"""
    service = get_facebook_marketing_service(session)
    campaign = await service.get_campaign(campaign_id)
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return campaign

@router.post("/campaigns/{campaign_id}/generate", tags=["Campaigns"])
async def generate_campaign_posts(
    campaign_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת פוסטים לקמפיין"""
    service = get_facebook_marketing_service(session)
    
    campaign = await service.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # יצירת הפוסטים (יכול לקחת זמן)
    posts = await service.generate_campaign_posts(campaign_id)
    await session.commit()
    
    return {
        "message": f"Generated {len(posts)} posts",
        "campaign_id": campaign_id,
        "posts_count": len(posts)
    }


# ========== Posts Endpoints ==========

@router.get("/posts", response_model=List[PostResponse], tags=["Posts"])
async def get_posts(
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת רשימת פוסטים"""
    query = select(FacebookPost).order_by(FacebookPost.created_at.desc())
    
    if campaign_id:
        query = query.where(FacebookPost.campaign_id == campaign_id)
    if status:
        query = query.where(FacebookPost.status == status)
    
    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

@router.get("/posts/pending", response_model=List[PostResponse], tags=["Posts"])
async def get_pending_posts(
    campaign_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת פוסטים ממתינים לאישור"""
    service = get_facebook_marketing_service(session)
    posts = await service.get_pending_posts(campaign_id)
    return posts

@router.get("/posts/{post_id}", response_model=PostResponse, tags=["Posts"])
async def get_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת פרטי פוסט"""
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return post

@router.put("/posts/{post_id}", response_model=PostResponse, tags=["Posts"])
async def update_post(
    post_id: int,
    data: PostUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון פוסט"""
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if data.content:
        post.content = data.content
    
    await session.commit()
    await session.refresh(post)
    return post

@router.post("/posts/{post_id}/approve", response_model=PostResponse, tags=["Posts"])
async def approve_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """אישור פוסט"""
    service = get_facebook_marketing_service(session)
    post = await service.approve_post(post_id)
    await session.commit()
    return post

@router.post("/posts/{post_id}/reject", response_model=PostResponse, tags=["Posts"])
async def reject_post(
    post_id: int,
    reason: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """דחיית פוסט"""
    service = get_facebook_marketing_service(session)
    post = await service.reject_post(post_id, reason)
    await session.commit()
    return post

@router.post("/posts/{post_id}/publish", response_model=PostResponse, tags=["Posts"])
async def publish_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """פרסום פוסט"""
    service = get_facebook_marketing_service(session)
    post = await service.publish_post(post_id)
    await session.commit()
    return post


# ========== Replies Endpoints ==========

@router.get("/replies", response_model=List[ReplyResponse], tags=["Replies"])
async def get_replies(
    post_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת תגובות"""
    query = select(FacebookReply).order_by(FacebookReply.created_at.desc())
    
    if post_id:
        query = query.where(FacebookReply.post_id == post_id)
    if status:
        query = query.where(FacebookReply.status == status)
    
    query = query.limit(limit)
    result = await session.execute(query)
    return result.scalars().all()

@router.get("/replies/pending", response_model=List[ReplyResponse], tags=["Replies"])
async def get_pending_replies(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת תגובות ממתינות לטיפול"""
    service = get_facebook_marketing_service(session)
    replies = await service.get_pending_replies()
    return replies

@router.post("/replies/{reply_id}/generate", response_model=ReplyResponse, tags=["Replies"])
async def generate_reply_response(
    reply_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת תשובה מוצעת לתגובה"""
    service = get_facebook_marketing_service(session)
    reply = await service.generate_reply_response(reply_id)
    await session.commit()
    return reply

@router.post("/replies/{reply_id}/respond", response_model=ReplyResponse, tags=["Replies"])
async def send_reply_response(
    reply_id: int,
    data: ReplyResponseAction,
    session: AsyncSession = Depends(get_async_session)
):
    """אישור ושליחת תשובה"""
    service = get_facebook_marketing_service(session)
    reply = await service.approve_and_send_response(
        reply_id=reply_id,
        response_text=data.response_text,
        channel=data.channel
    )
    await session.commit()
    return reply

@router.post("/posts/{post_id}/sync-comments", tags=["Replies"])
async def sync_post_comments(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """סנכרון תגובות מפוסט"""
    service = get_facebook_marketing_service(session)
    replies = await service.sync_post_comments(post_id)
    await session.commit()
    
    return {
        "message": f"Synced {len(replies)} new comments",
        "post_id": post_id,
        "new_replies": len(replies)
    }


# ========== Statistics ==========

@router.get("/stats", tags=["Statistics"])
async def get_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת סטטיסטיקות"""
    service = get_facebook_marketing_service(session)
    return await service.get_stats()
