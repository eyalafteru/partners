"""
PartnerCalc OS - Facebook Marketing API
API endpoints לניהול פרסום בקבוצות פייסבוק
"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from pydantic import BaseModel, validator
from datetime import datetime
from loguru import logger

from app.database import get_async_session
from app.models.facebook_marketing import (
    FacebookGroup,
    FacebookCampaign,
    FacebookPost,
    FacebookReply,
    FacebookConversation,
    FacebookMessage,
    FacebookPostTemplate,
    FacebookActionLog,
)
from app.models.lead_hunter import LeadPost
from app.services.facebook_marketing_service import get_facebook_marketing_service
from app.services.apify_service import get_apify_service

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
    # New fields
    calculator_id: Optional[int] = None
    calculator_mode: str = "all"  # specific, all, category
    calculator_category: Optional[str] = None
    strategy_ids: List[int] = []
    link_placement: str = "in_post"  # in_post, first_comment, none
    auto_responder_enabled: bool = False
    auto_responder_type: str = "comment"  # comment, messenger, ai_decide
    auto_responder_template: Optional[str] = None
    auto_responder_delay_minutes: int = 5
    auto_responder_daily_limit: int = 50
    media_preference: Optional[str] = "image"  # image, video, both, none

class CampaignResponse(BaseModel):
    id: int
    name: str
    topic: str
    target_audience: Optional[str]
    status: str
    image_percentage: int
    target_group_ids: Optional[List[int]] = []
    total_posts_generated: int
    total_posts_approved: int
    total_posts_published: int
    total_replies: int
    created_at: datetime
    # New fields
    calculator_id: Optional[int] = None
    calculator_mode: Optional[str] = "all"
    calculator_category: Optional[str] = None
    strategy_ids: Optional[List[int]] = None
    link_placement: Optional[str] = "in_post"
    auto_responder_enabled: Optional[bool] = False
    auto_responder_type: Optional[str] = "comment"
    auto_responder_template: Optional[str] = None
    auto_responder_delay_minutes: Optional[int] = 5
    auto_responder_daily_limit: Optional[int] = 50
    media_preference: Optional[str] = "image"
    
    @validator('strategy_ids', 'target_group_ids', pre=True, always=True)
    def convert_none_to_list(cls, v):
        return v if v is not None else []
    
    class Config:
        from_attributes = True

class PostResponse(BaseModel):
    id: int
    campaign_id: Optional[int]
    group_id: int
    content: str
    has_image: bool
    image_url: Optional[str]
    youtube_url: Optional[str] = None
    status: str
    rejection_reason: Optional[str]
    publish_error: Optional[str] = None
    replies_count: int
    published_at: Optional[datetime]
    created_at: datetime
    # New fields
    calculator_id: Optional[int] = None
    strategy_id: Optional[int] = None
    first_comment_content: Optional[str] = None
    first_comment_posted: bool = False
    auto_replies_sent: int = 0
    # 🐞 DEBUG
    debug_ai_prompt: Optional[str] = None
    
    class Config:
        from_attributes = True

class PostUpdate(BaseModel):
    content: Optional[str] = None
    fb_post_url: Optional[str] = None
    status: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    topic: Optional[str] = None
    target_audience: Optional[str] = None
    image_percentage: Optional[int] = None
    status: Optional[str] = None
    target_group_ids: Optional[List[int]] = None
    # New fields
    calculator_id: Optional[int] = None
    calculator_mode: Optional[str] = None
    calculator_category: Optional[str] = None
    strategy_ids: Optional[List[int]] = None
    link_placement: Optional[str] = None
    auto_responder_enabled: Optional[bool] = None
    auto_responder_type: Optional[str] = None
    auto_responder_template: Optional[str] = None
    auto_responder_delay_minutes: Optional[int] = None
    auto_responder_daily_limit: Optional[int] = None

class ReplyResponse(BaseModel):
    id: int
    post_id: int
    fb_user_name: Optional[str]
    fb_user_profile_url: Optional[str]
    fb_user_profile_pic: Optional[str] = None
    message: str
    ai_detected_intent: Optional[str]
    ai_analysis: Optional[dict] = None
    wants_private: bool
    status: str
    suggested_response: Optional[str]
    suggested_channel: Optional[str]
    actual_response: Optional[str]
    response_channel: Optional[str] = None
    responded_at: Optional[datetime] = None
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

class BulkGroupItem(BaseModel):
    id: str  # fb_group_id
    name: str
    url: Optional[str] = None

class BulkImportRequest(BaseModel):
    groups: List[BulkGroupItem]
    category: Optional[str] = None

class BulkImportResponse(BaseModel):
    imported: int
    skipped: int
    total: int
    message: str

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
    """הוספת קבוצה חדשה, או הפעלה מחדש של קבוצה שבוטלה"""
    # Check if group already exists (possibly soft-deleted)
    result = await session.execute(
        select(FacebookGroup).where(FacebookGroup.fb_group_id == data.fb_group_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        if existing.is_active:
            raise HTTPException(status_code=409, detail=f"קבוצה עם מזהה {data.fb_group_id} כבר קיימת במערכת")
        # Reactivate soft-deleted group and update its details
        existing.is_active = True
        if data.name:
            existing.name = data.name
        if data.url:
            existing.url = data.url
        if data.category:
            existing.category = data.category
        await session.commit()
        await session.refresh(existing)
        return existing
    
    service = get_facebook_marketing_service(session)
    group = await service.add_group(**data.model_dump())
    await session.commit()
    return group

@router.post("/groups/bulk-import", response_model=BulkImportResponse, tags=["Groups"])
async def bulk_import_groups(
    data: BulkImportRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יבוא מאסיבי של קבוצות מפייסבוק.
    מנקה אוטומטית את השמות מ-"Last active..." 
    """
    import re
    
    imported = 0
    skipped = 0
    
    for group_item in data.groups:
        # ניקוי שם הקבוצה מ-"Last active..."
        clean_name = re.sub(r'Last active.*$', '', group_item.name).strip()
        if not clean_name:
            clean_name = f"Group {group_item.id}"
        
        # בדיקה אם הקבוצה כבר קיימת
        result = await session.execute(
            select(FacebookGroup).where(FacebookGroup.fb_group_id == group_item.id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            skipped += 1
            continue
        
        # יצירת קבוצה חדשה
        new_group = FacebookGroup(
            fb_group_id=group_item.id,
            name=clean_name,
            url=group_item.url or f"https://www.facebook.com/groups/{group_item.id}",
            category=data.category,
            is_active=True
        )
        session.add(new_group)
        imported += 1
    
    await session.commit()
    
    return BulkImportResponse(
        imported=imported,
        skipped=skipped,
        total=len(data.groups),
        message=f"יובאו {imported} קבוצות חדשות, {skipped} קבוצות כבר היו קיימות"
    )

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
    # Debug logging
    logger.info(f"📥 Creating campaign with data: {data.model_dump()}")
    logger.info(f"📥 media_preference received: {data.media_preference}")
    
    service = get_facebook_marketing_service(session)
    campaign = await service.create_campaign(**data.model_dump())
    await session.commit()
    
    logger.info(f"📤 Campaign created with media_preference: {campaign.media_preference}")
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

@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse, tags=["Campaigns"])
async def update_campaign(
    campaign_id: int,
    data: CampaignUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון קמפיין"""
    result = await session.execute(
        select(FacebookCampaign).where(FacebookCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # עדכון שדות
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(campaign, field, value)
    
    await session.commit()
    await session.refresh(campaign)
    
    return campaign

@router.delete("/campaigns/{campaign_id}", tags=["Campaigns"])
async def delete_campaign(
    campaign_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """מחיקת קמפיין וכל הפוסטים שלו"""
    # FacebookCampaign and FacebookPost are already imported at the top of the file
    
    # שליפת הקמפיין
    result = await session.execute(
        select(FacebookCampaign).where(FacebookCampaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # מחיקת כל הפוסטים של הקמפיין (כולל פורסמו)
    await session.execute(
        delete(FacebookPost).where(FacebookPost.campaign_id == campaign_id)
    )
    
    # מחיקת הקמפיין
    await session.delete(campaign)
    await session.commit()
    
    return {"message": f"Campaign '{campaign.name}' deleted successfully"}

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


@router.get("/posts/{post_id}/debug", tags=["Posts", "Debug"])
async def get_post_debug(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    🐞 DEBUG: צפייה בפרומפט המלא שנשלח ל-AI עבור פוסט ספציפי
    
    משמש לאיתור בעיות כמו:
    - עובדות שגויות
    - מספרים ממוצאים
    - התעלמות מהוראות
    """
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # קבלת פרטים נוספים
    group_name = None
    strategy_name = None
    calculator_name = None
    
    if post.group_id:
        group_result = await session.execute(
            select(FacebookGroup.name).where(FacebookGroup.id == post.group_id)
        )
        group_name = group_result.scalar_one_or_none()
    
    if post.strategy_id:
        from app.models.post_strategy import PostStrategy
        strategy_result = await session.execute(
            select(PostStrategy.name).where(PostStrategy.id == post.strategy_id)
        )
        strategy_name = strategy_result.scalar_one_or_none()
    
    if post.calculator_id:
        from app.models.calculator import Calculator
        calc_result = await session.execute(
            select(Calculator.name).where(Calculator.id == post.calculator_id)
        )
        calculator_name = calc_result.scalar_one_or_none()
    
    return {
        "post_id": post.id,
        "status": post.status,
        "group_name": group_name,
        "strategy_name": strategy_name,
        "calculator_name": calculator_name,
        "generated_content": post.content,
        "debug_ai_prompt": post.debug_ai_prompt,
        "has_debug_prompt": bool(post.debug_ai_prompt),
        "created_at": post.created_at
    }


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
    if data.fb_post_url:
        post.fb_post_url = data.fb_post_url
    if data.status:
        post.status = data.status
    
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

@router.post("/posts/{post_id}/reject", tags=["Posts"])
async def reject_post(
    post_id: int,
    reason: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """דחיית ומחיקת פוסט - מחזיר את פרטי הקבוצה והקמפיין לייצור מחדש"""
    # Get post info before deleting
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Save info for response
    group_id = post.group_id
    campaign_id = post.campaign_id
    
    # Delete the post
    await session.delete(post)
    await session.commit()
    
    return {
        "message": "Post deleted",
        "group_id": group_id,
        "campaign_id": campaign_id,
        "can_regenerate": campaign_id is not None
    }


@router.post("/posts/regenerate-for-group", response_model=PostResponse, tags=["Posts"])
async def regenerate_post_for_group(
    campaign_id: int,
    group_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """יצירת פוסט חדש לקבוצה בקמפיין"""
    service = get_facebook_marketing_service(session)
    
    # Generate new post for this group
    post = await service.generate_single_post(campaign_id, group_id)
    
    if not post:
        raise HTTPException(status_code=500, detail="Failed to generate post")
    
    await session.commit()
    await session.refresh(post)
    return post

@router.post("/posts/{post_id}/publish", response_model=PostResponse, tags=["Posts"])
async def publish_post(
    post_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """פרסום פוסט"""
    try:
        service = get_facebook_marketing_service(session)
        post = await service.publish_post(post_id)
        await session.commit()
        return post
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class BulkPublishRequest(BaseModel):
    post_ids: List[int]
    approve_first: bool = True  # אם True, יאשר לפני פרסום


class BulkPublishResult(BaseModel):
    post_id: int
    success: bool
    status: Optional[str] = None
    error: Optional[str] = None


@router.post("/posts/bulk-publish", tags=["Posts"])
async def bulk_publish_posts(
    data: BulkPublishRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """פרסום מרובה של פוסטים"""
    service = get_facebook_marketing_service(session)
    results = []
    
    for post_id in data.post_ids:
        try:
            # Get post
            result = await session.execute(
                select(FacebookPost).where(FacebookPost.id == post_id)
            )
            post = result.scalar_one_or_none()
            
            if not post:
                results.append(BulkPublishResult(
                    post_id=post_id,
                    success=False,
                    error="Post not found"
                ))
                continue
            
            # Approve if needed
            if data.approve_first and post.status == "pending_approval":
                post.status = "approved"
                await session.flush()
            
            # Publish
            if post.status == "approved":
                published_post = await service.publish_post(post_id)
                await session.commit()
                results.append(BulkPublishResult(
                    post_id=post_id,
                    success=True,
                    status=published_post.status
                ))
            else:
                results.append(BulkPublishResult(
                    post_id=post_id,
                    success=False,
                    error=f"Post status is {post.status}, expected approved"
                ))
                
        except Exception as e:
            results.append(BulkPublishResult(
                post_id=post_id,
                success=False,
                error=str(e)
            ))
    
    return {
        "total": len(data.post_ids),
        "successful": len([r for r in results if r.success]),
        "failed": len([r for r in results if not r.success]),
        "results": results
    }


class RegenerateRequest(BaseModel):
    model: Optional[str] = None  # gpt-4o-mini, claude-sonnet-4, etc.


@router.post("/posts/{post_id}/regenerate", response_model=PostResponse, tags=["Posts"])
async def regenerate_post(
    post_id: int,
    data: RegenerateRequest = RegenerateRequest(),
    session: AsyncSession = Depends(get_async_session)
):
    """ייצור מחדש של פוסט"""
    from app.services.post_generator_service import get_post_generator_service
    
    # Get post with group info
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get group
    group_result = await session.execute(
        select(FacebookGroup).where(FacebookGroup.id == post.group_id)
    )
    group = group_result.scalar_one_or_none()
    
    # Get campaign
    campaign = None
    if post.campaign_id:
        campaign_result = await session.execute(
            select(FacebookCampaign).where(FacebookCampaign.id == post.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
    
    # Generate new content
    generator = get_post_generator_service()
    new_content = await generator.generate_post_variation(
        topic=campaign.topic if campaign else "מחשבונים פיננסיים להטמעה בחינם",
        group_name=group.name if group else "",
        target_audience=campaign.target_audience if campaign else "",
        previous_posts=[post.content],  # Avoid same content
        model=data.model
    )
    
    if not new_content:
        raise HTTPException(status_code=500, detail="Failed to regenerate post")
    
    post.content = new_content
    post.status = "pending_approval"
    
    await session.commit()
    await session.refresh(post)
    return post


class ImageGenerationRequest(BaseModel):
    style: str = "eyal"  # "eyal" = עם אייל, "generic" = גנרית
    regenerate: bool = False  # האם לייצר מחדש


@router.post("/posts/{post_id}/add-image", response_model=PostResponse, tags=["Posts"])
async def add_image_to_post(
    post_id: int,
    data: ImageGenerationRequest = ImageGenerationRequest(),
    session: AsyncSession = Depends(get_async_session)
):
    """הוספת/ייצור מחדש של תמונה לפוסט"""
    from app.services.post_generator_service import get_post_generator_service
    from app.services.replicate_service import get_replicate_service
    
    result = await session.execute(
        select(FacebookPost).where(FacebookPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Generate dynamic image prompt
    generator = get_post_generator_service()
    image_prompt = await generator.generate_viral_image_prompt(
        post_content=post.content,
        style=data.style,  # "eyal" or "generic"
        previous_prompt=post.image_prompt if data.regenerate else None
    )
    
    if not image_prompt:
        raise HTTPException(status_code=500, detail="Failed to generate image prompt")
    
    # Generate image
    replicate_service = get_replicate_service()
    image_url = await replicate_service.generate_post_image(
        image_prompt=image_prompt,
        use_lora=(data.style == "eyal")  # Use LoRA only for eyal style
    )
    
    if not image_url:
        raise HTTPException(status_code=500, detail="Failed to generate image")
    
    post.has_image = True
    post.image_prompt = image_prompt
    post.image_url = image_url
    
    await session.commit()
    await session.refresh(post)
    return post


@router.get("/anti-spam/stats", tags=["Anti-Spam"])
async def get_anti_spam_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת סטטיסטיקות Anti-Spam"""
    import traceback
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from app.services.anti_spam_service import get_anti_spam_service
        
        anti_spam = get_anti_spam_service(session)
        stats = await anti_spam.get_posting_stats()
        return stats
    except Exception as e:
        logger.error(f"Anti-Spam stats error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anti-spam/can-post", tags=["Anti-Spam"])
async def check_can_post(
    group_id: Optional[int] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """בדיקה האם מותר לפרסם"""
    from app.services.anti_spam_service import get_anti_spam_service
    
    anti_spam = get_anti_spam_service(session)
    
    if group_id:
        can_post, reason = await anti_spam.can_post_to_group(group_id)
    else:
        can_post, reason = await anti_spam.can_post_now()
    
    return {
        "can_post": can_post,
        "reason": reason,
        "group_id": group_id
    }


@router.get("/ai/models", tags=["AI"])
async def get_available_models():
    """קבלת רשימת מודלים זמינים"""
    from app.services.post_generator_service import get_post_generator_service
    
    generator = get_post_generator_service()
    return {
        "models": generator.get_available_models(),
        "default": generator.default_model
    }


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
    logger.info(f"📩 Generate reply requested: reply_id={reply_id}")
    service = get_facebook_marketing_service(session)
    try:
        reply = await service.generate_reply_response(reply_id)
    except ValueError as e:
        logger.error(f"❌ Generate reply ValueError: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Generate reply failed")
        logger.error(f"❌ Generate reply error: {e!s}")
        raise HTTPException(status_code=503, detail=f"שגיאה ביצירת תשובה: {e!s}")
    await session.commit()
    return reply

@router.post("/replies/{reply_id}/respond", tags=["Replies"])
async def send_reply_response(
    reply_id: int,
    data: ReplyResponseAction,
    session: AsyncSession = Depends(get_async_session)
):
    """אישור ושליחת תשובה"""
    from fastapi.responses import JSONResponse
    service = get_facebook_marketing_service(session)
    reply, send_error = await service.approve_and_send_response(
        reply_id=reply_id,
        response_text=data.response_text,
        channel=data.channel
    )
    await session.commit()
    reply_data = ReplyResponse.model_validate(reply).model_dump(mode="json")
    if send_error:
        reply_data["send_error"] = send_error[:500]
        return JSONResponse(content=reply_data, status_code=200)
    return reply_data


@router.post("/replies/{reply_id}/ignore", response_model=ReplyResponse, tags=["Replies"])
async def ignore_reply(
    reply_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """סימון תגובה כ-ignored (לא רלוונטי / ספאם)"""
    result = await session.execute(
        select(FacebookReply).where(FacebookReply.id == reply_id)
    )
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    reply.status = "ignored"
    await session.commit()
    return reply


@router.post("/replies/{reply_id}/mark-responded", response_model=ReplyResponse, tags=["Replies"])
async def mark_reply_responded(
    reply_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """סימון תגובה כנענתה (לאחר פרסום ידני בפייסבוק)"""
    from datetime import datetime
    
    result = await session.execute(
        select(FacebookReply).where(FacebookReply.id == reply_id)
    )
    reply = result.scalar_one_or_none()
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    reply.status = "responded"
    reply.responded_at = datetime.utcnow()
    if not reply.actual_response:
        reply.actual_response = reply.suggested_response
    
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


@router.get("/replies/stats", tags=["Replies"])
async def get_reply_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """סטטיסטיקות תגובות - כמה ממתינות, כמה נענו היום, פירוט לפי intent"""
    service = get_facebook_marketing_service(session)
    stats = await service.get_reply_stats()
    return stats


# ========== Calculators ==========

@router.get("/calculators", tags=["Calculators"])
async def get_calculators_for_facebook(
    active_only: bool = True,
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """שליפת מחשבונים לבחירה בקמפיין"""
    from app.models.calculator import Calculator
    
    query = select(Calculator)
    if active_only:
        query = query.where(Calculator.is_active == True)
    if category:
        query = query.where(Calculator.category == category)
    
    result = await session.execute(query)
    calculators = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "url": c.target_url,
            "target_url": c.target_url,
            "has_summary": bool(c.ai_summary) if hasattr(c, 'ai_summary') else False,
            "youtube_url": c.youtube_url if hasattr(c, 'youtube_url') else None,
            "demo_video_url": c.demo_video_url if hasattr(c, 'demo_video_url') else None,
        }
        for c in calculators
    ]

@router.get("/calculator-categories", tags=["Calculators"])
async def get_calculator_categories(
    session: AsyncSession = Depends(get_async_session)
):
    """שליפת קטגוריות מחשבונים"""
    from app.models.calculator import Calculator
    
    result = await session.execute(
        select(Calculator.category).distinct().where(Calculator.category.isnot(None))
    )
    categories = [row[0] for row in result.fetchall() if row[0]]
    
    return {"categories": categories}


# ========== Statistics ==========

@router.get("/stats", tags=["Statistics"])
async def get_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת סטטיסטיקות"""
    service = get_facebook_marketing_service(session)
    return await service.get_stats()


# ========== Publishing Profiles (מעבר בין יוזרים) ==========

class ProfileItem(BaseModel):
    id: int
    name: str
    is_active: bool
    updated_at: Optional[datetime] = None


@router.get("/profiles", response_model=List[ProfileItem], tags=["Cookies"])
async def list_publishing_profiles():
    """רשימת פרופילי פרסום (למשל אייל / שלי). הפרופיל הפעיל משמש לפרסום ולסנכרון."""
    from app.database import get_async_session_context
    from sqlalchemy import text as sa_text
    try:
        async with get_async_session_context() as db:
            r = await db.execute(sa_text(
                "SELECT id, name, is_active, updated_at FROM facebook_publishing_profiles ORDER BY id"
            ))
            rows = r.fetchall()
        return [
            ProfileItem(id=row[0], name=row[1], is_active=bool(row[2]), updated_at=row[3])
            for row in rows
        ]
    except Exception as e:
        logger.warning(f"🍪 list profiles: {e}")
        return []


class CreateProfileRequest(BaseModel):
    name: str


@router.post("/profiles", response_model=ProfileItem, tags=["Cookies"])
async def create_publishing_profile(data: CreateProfileRequest):
    """יצירת פרופיל פרסום חדש (למשל 'שלי'). אחר כך אפשר להגדיר כפעיל ולסנכרן אליו cookies."""
    from app.database import get_async_session_context
    from sqlalchemy import text as sa_text
    name = (data.name or "").strip() or "פרופיל חדש"
    async with get_async_session_context() as db:
        await db.execute(sa_text("""
            INSERT INTO facebook_publishing_profiles (name, is_active, updated_at, created_at)
            VALUES (:name, 0, NOW(), NOW())
        """), {"name": name})
        await db.commit()
        r = await db.execute(sa_text(
            "SELECT id, name, is_active, updated_at FROM facebook_publishing_profiles WHERE name = :name ORDER BY id DESC LIMIT 1"
        ), {"name": name})
        row = r.fetchone()
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create profile")
    logger.info(f"🍪 Profile created: {name} (id={row[0]})")
    return ProfileItem(id=row[0], name=row[1], is_active=bool(row[2]), updated_at=row[3])


@router.put("/profiles/{profile_id}/set-active", tags=["Cookies"])
async def set_active_profile(profile_id: int):
    """הגדרת פרופיל כפעיל – מכאן ואילך פרסום וסנכרון ישתמשו בפרופיל הזה."""
    from app.database import get_async_session_context
    from sqlalchemy import text as sa_text
    async with get_async_session_context() as db:
        await db.execute(sa_text(
            "UPDATE facebook_publishing_profiles SET is_active = 0"
        ))
        await db.execute(sa_text(
            "UPDATE facebook_publishing_profiles SET is_active = 1 WHERE id = :pid"
        ), {"pid": profile_id})
        await db.commit()
    apify = get_apify_service()
    apify.reload_cookies()
    logger.info(f"🍪 Active profile set to id={profile_id}")
    return {"status": "ok", "activeProfileId": profile_id}


# ========== Cookie Management ==========

class CookieUploadRequest(BaseModel):
    cookies: list  # JSON array of cookie objects
    profile_id: Optional[int] = None  # אם לא נשלח – שומר בפרופיל הפעיל


@router.post("/cookies/upload", tags=["Cookies"])
async def upload_cookies(request: CookieUploadRequest):
    """
    העלאת cookies של פייסבוק.
    אם יש פרופילים: שומר בפרופיל שצוין (profile_id) או בפרופיל הפעיל.
    אם אין פרופילים: שומר ב-facebook_cookie_storage id=1 ו-.env (תאימות לאחור).
    """
    import json
    import os
    import hashlib
    import platform
    
    cookies = request.cookies
    profile_id = request.profile_id
    
    cookie_names = {c.get("name") for c in cookies if isinstance(c, dict)}
    required_cookies = {"c_user", "xs", "fr"}
    missing = required_cookies - cookie_names
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"חסרים cookies חיוניים: {', '.join(missing)}. יש לייצא מפייסבוק עם הפלאגין."
        )
    
    cookie_json = json.dumps(cookies, ensure_ascii=False)
    updated_at = datetime.utcnow().isoformat()
    cookie_hash = hashlib.sha256(cookie_json.encode()).hexdigest()[:16]
    source_machine = platform.node()
    db_saved = False
    
    from app.database import get_async_session_context
    from sqlalchemy import text as sa_text
    
    try:
        async with get_async_session_context() as db_session:
            # יש טבלת פרופילים?
            r = await db_session.execute(sa_text(
                "SELECT id FROM facebook_publishing_profiles LIMIT 1"
            ))
            has_profiles = r.scalar() is not None
            
            if has_profiles:
                target_id = profile_id
                if target_id is None:
                    r2 = await db_session.execute(sa_text(
                        "SELECT id FROM facebook_publishing_profiles WHERE is_active = 1 LIMIT 1"
                    ))
                    target_id = r2.scalar()
                if target_id is None:
                    r3 = await db_session.execute(sa_text(
                        "SELECT id FROM facebook_publishing_profiles ORDER BY id LIMIT 1"
                    ))
                    target_id = r3.scalar()
                if target_id is not None:
                    await db_session.execute(sa_text("""
                        UPDATE facebook_publishing_profiles
                        SET cookie_json = :cj, cookie_hash = :ch, source_machine = :sm, updated_at = NOW()
                        WHERE id = :pid
                    """), {"cj": cookie_json, "ch": cookie_hash, "sm": source_machine, "pid": target_id})
                    await db_session.commit()
                    db_saved = True
                    logger.info(f"🍪 ✅ Cookies saved to profile id={target_id} (hash: {cookie_hash})")
            
            if not db_saved:
                # Legacy: facebook_cookie_storage
                await db_session.execute(sa_text(
                    "INSERT INTO facebook_cookie_storage (id, cookie_json, cookie_hash, source_machine, updated_at, created_at) "
                    "VALUES (1, :cookie_json, :cookie_hash, :source_machine, NOW(), NOW()) "
                    "ON DUPLICATE KEY UPDATE "
                    "cookie_json = VALUES(cookie_json), cookie_hash = VALUES(cookie_hash), "
                    "source_machine = VALUES(source_machine), updated_at = NOW()"
                ), {"cookie_json": cookie_json, "cookie_hash": cookie_hash, "source_machine": source_machine})
                await db_session.commit()
                db_saved = True
                logger.info(f"🍪 ✅ Cookies saved to DB legacy (hash: {cookie_hash})")
    except Exception as db_err:
        logger.warning(f"🍪 ⚠️ Failed to save cookies to DB: {db_err}")
    
    if not db_saved:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().split("\n")
            new_lines = []
            for line in lines:
                if line.startswith("FACEBOOK_COOKIE="):
                    new_lines.append(f"FACEBOOK_COOKIE={cookie_json}")
                elif line.startswith("FACEBOOK_COOKIE_UPDATED_AT="):
                    new_lines.append(f"FACEBOOK_COOKIE_UPDATED_AT={updated_at}")
                else:
                    new_lines.append(line)
            if not any(line.startswith("FACEBOOK_COOKIE=") for line in lines):
                new_lines.append(f"FACEBOOK_COOKIE={cookie_json}")
            if not any(line.startswith("FACEBOOK_COOKIE_UPDATED_AT=") for line in lines):
                new_lines.append(f"FACEBOOK_COOKIE_UPDATED_AT={updated_at}")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines))
        except Exception as env_err:
            logger.warning(f"🍪 ⚠️ Failed to save to .env: {env_err}")
    
    apify = get_apify_service()
    apify.reload_cookies()
    logger.info(f"🍪 Facebook cookies updated: {len(cookies)} cookies")
    return {
        "status": "success",
        "message": f"Cookies עודכנו בהצלחה ({len(cookies)} cookies)",
        "cookieCount": len(cookies),
        "updatedAt": updated_at,
        "savedToDb": db_saved,
    }


@router.get("/cookies/status", tags=["Cookies"])
async def get_cookie_status():
    """
    בדיקת סטטוס cookies + רשימת פרופילים והפרופיל הפעיל.
    """
    import json
    from app.config import get_settings
    from app.services.facebook_cookie_resolver import get_facebook_cookies_for_publishing
    
    cookie_str, profile_name = get_facebook_cookies_for_publishing()
    source = "profile" if profile_name else ("database" if cookie_str else "none")
    db_updated_at = None
    db_source_machine = None
    
    if not cookie_str:
        current_settings = get_settings()
        cookie_str = current_settings.facebook_cookie
        if cookie_str:
            source = "env"
    
    profiles = []
    active_profile = None
    try:
        from app.database import get_async_session_context
        from sqlalchemy import text as sa_text
        async with get_async_session_context() as db_session:
            r = await db_session.execute(sa_text(
                "SELECT id, name, is_active, updated_at FROM facebook_publishing_profiles ORDER BY id"
            ))
            for row in r.fetchall():
                profiles.append({"id": row[0], "name": row[1], "is_active": bool(row[2]), "updated_at": row[3].isoformat() if row[3] else None})
                if row[2]:
                    active_profile = {"id": row[0], "name": row[1]}
            if not active_profile and profiles:
                active_profile = {"id": profiles[0]["id"], "name": profiles[0]["name"]}
    except Exception:
        pass
    
    has_cookie = bool(cookie_str)
    cookie_count = 0
    cookie_names = []
    if has_cookie:
        try:
            cookies = json.loads(cookie_str) if isinstance(cookie_str, str) else cookie_str
            cookie_count = len(cookies)
            cookie_names = [c.get("name") for c in cookies if isinstance(c, dict)]
        except Exception:
            pass
    essential = {"c_user", "xs", "fr"}
    has_essential = essential.issubset(set(cookie_names))
    current_settings = get_settings()
    
    return {
        "status": "valid" if (has_cookie and has_essential) else "expired",
        "hasCookie": has_cookie,
        "hasEssentialCookies": has_essential,
        "cookieCount": cookie_count,
        "cookieNames": cookie_names,
        "lastUpdated": db_updated_at or current_settings.facebook_cookie_updated_at or None,
        "source": source,
        "sourceMachine": db_source_machine,
        "profiles": profiles,
        "activeProfile": active_profile,
    }


@router.get("/cookies/open-login", tags=["Cookies"])
async def open_facebook_login():
    """
    פתיחת Chrome לדף ההתחברות של פייסבוק
    עובד רק כשה-backend רץ מקומית
    """
    import webbrowser
    try:
        webbrowser.open("https://www.facebook.com/")
        logger.info("🍪 🌐 Opened Chrome to Facebook for login")
        return {"status": "opened", "message": "Chrome opened to Facebook"}
    except Exception as e:
        logger.error(f"🍪 ❌ Failed to open browser: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to open browser: {str(e)}")


# ========== Action Log ==========

@router.get("/action-log", tags=["Action Log"])
async def get_action_log(
    limit: int = Query(50, ge=1, le=500),
    action_type: Optional[str] = Query(None),
    profile_name: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """
    לוג פעולות פייסבוק -- לזיהוי חסימות ומעקב אחרי כל אינטראקציה.
    """
    query = select(FacebookActionLog).order_by(FacebookActionLog.created_at.desc())

    if action_type:
        query = query.where(FacebookActionLog.action_type == action_type)
    if profile_name:
        query = query.where(FacebookActionLog.profile_name == profile_name)
    if success is not None:
        query = query.where(FacebookActionLog.success == success)

    query = query.limit(limit)
    result = await session.execute(query)
    rows = result.scalars().all()

    return [
        {
            "id": r.id,
            "action_type": r.action_type,
            "method": r.method,
            "profile_name": r.profile_name,
            "target_url": r.target_url,
            "post_id": r.post_id,
            "reply_id": r.reply_id,
            "group_name": r.group_name,
            "apify_run_id": r.apify_run_id,
            "success": r.success,
            "error_message": r.error_message,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/action-log/summary", tags=["Action Log"])
async def get_action_log_summary(
    hours: int = Query(24, ge=1, le=720),
    session: AsyncSession = Depends(get_async_session),
):
    """
    סיכום פעולות פייסבוק לפי סוג -- כמה הצליחו, כמה נכשלו.
    """
    from datetime import timedelta
    from sqlalchemy import text
    since = datetime.utcnow() - timedelta(hours=hours)
    raw = await session.execute(text("""
        SELECT action_type, method, profile_name,
               COUNT(*) as total,
               SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
               SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as fail_count,
               ROUND(AVG(duration_ms)) as avg_duration_ms
        FROM facebook_action_log
        WHERE created_at >= :since
        GROUP BY action_type, method, profile_name
        ORDER BY total DESC
    """), {"since": since})

    rows = raw.fetchall()
    return {
        "hours": hours,
        "since": since.isoformat(),
        "groups": [
            {
                "action_type": r[0],
                "method": r[1],
                "profile_name": r[2],
                "total": r[3],
                "success_count": r[4] or 0,
                "fail_count": r[5] or 0,
                "avg_duration_ms": r[6],
            }
            for r in rows
        ],
    }


# ========== Chrome Extension Tasks ==========

@router.get("/extension/pending-tasks", tags=["Chrome Extension"])
async def get_pending_extension_tasks(
    session: AsyncSession = Depends(get_async_session),
):
    """
    התוסף שואל: יש משימות תגובה ממתינות?
    בודק קודם משימות Facebook Marketing, אח"כ Lead Hunter.
    """
    # --- 1) Facebook Marketing tasks (existing) ---
    result = await session.execute(
        select(FacebookReply)
        .where(FacebookReply.status == "pending_extension")
        .order_by(FacebookReply.created_at.asc())
        .limit(1)
    )
    reply = result.scalar_one_or_none()

    if reply:
        post_result = await session.execute(
            select(FacebookPost).where(FacebookPost.id == reply.post_id)
        )
        post = post_result.scalar_one_or_none()

        if not post or not post.fb_post_url:
            logger.warning(f"🔌 Extension task skipped - no post URL for reply {reply.id}")
            reply.status = "failed"
            reply.actual_response = reply.suggested_response
            await session.flush()
        else:
            reply.status = "extension_working"
            await session.flush()

            logger.info(f"🔌 📤 Extension picked up marketing task: reply {reply.id} for post {post.id}")

            return {
                "has_task": True,
                "task": {
                    "task_type": "marketing",
                    "reply_id": reply.id,
                    "post_id": post.id,
                    "post_url": post.fb_post_url,
                    "comment_id": reply.fb_comment_id,
                    "reply_message": reply.suggested_response or reply.actual_response,
                    "commenter_name": reply.fb_user_name,
                },
            }

    # --- 2) Lead Hunter auto-reply tasks ---
    lead_result = await session.execute(
        select(LeadPost)
        .where(LeadPost.auto_reply_status == "pending")
        .order_by(LeadPost.created_at.asc())
        .limit(1)
    )
    lead_post = lead_result.scalar_one_or_none()

    if lead_post:
        if not lead_post.post_url or not lead_post.ai_reply:
            logger.warning(f"🔌 Lead Hunter task skipped - no URL/reply for post {lead_post.id}")
            lead_post.auto_reply_status = "failed"
            await session.flush()
            return {"has_task": False}

        lead_post.auto_reply_status = "working"
        await session.flush()

        logger.info(f"🔌 📤 Extension picked up lead_hunter task: post {lead_post.id}")

        return {
            "has_task": True,
            "task": {
                "task_type": "lead_hunter",
                "lead_post_id": lead_post.id,
                "post_url": lead_post.post_url,
                "reply_message": lead_post.ai_reply,
                "reply_type": lead_post.reply_type or "text",
                "banner_type": lead_post.banner_type,
            },
        }

    return {"has_task": False}


class ExtensionTaskResult(BaseModel):
    task_type: str = "marketing"
    reply_id: Optional[int] = None
    lead_post_id: Optional[int] = None
    success: bool
    error: Optional[str] = None
    screenshot_url: Optional[str] = None


@router.post("/extension/task-result", tags=["Chrome Extension"])
async def report_extension_task_result(
    body: ExtensionTaskResult,
    session: AsyncSession = Depends(get_async_session),
):
    """
    התוסף מדווח: משימה הצליחה / נכשלה.
    תומך במשימות marketing (FacebookReply) ו-lead_hunter (LeadPost).
    """
    from app.services.facebook_action_logger import (
        fb_action_log, ACTION_REPLY, METHOD_CHROME_EXT,
    )

    if body.task_type == "lead_hunter" and body.lead_post_id:
        return await _handle_lead_hunter_result(body, session)

    if not body.reply_id:
        raise HTTPException(status_code=400, detail="reply_id is required for marketing tasks")

    result = await session.execute(
        select(FacebookReply).where(FacebookReply.id == body.reply_id)
    )
    reply = result.scalar_one_or_none()

    if not reply:
        raise HTTPException(status_code=404, detail=f"Reply {body.reply_id} not found")

    tracker = fb_action_log(
        ACTION_REPLY, METHOD_CHROME_EXT,
        target_url=None,
        post_id=reply.post_id,
        reply_id=reply.id,
    )

    if body.success:
        reply.status = "responded"
        reply.response_channel = "comment"
        reply.actual_response = reply.suggested_response or reply.actual_response
        reply.responded_at = datetime.utcnow()
        await tracker.finish(success=True)
        logger.info(f"🔌 ✅ Extension completed marketing reply {reply.id}")
    else:
        reply.status = "extension_failed"
        await tracker.finish(success=False, error_message=body.error)
        logger.error(f"🔌 ❌ Extension failed marketing reply {reply.id}: {body.error}")

    await session.flush()

    return {
        "ok": True,
        "task_type": "marketing",
        "reply_id": reply.id,
        "new_status": reply.status,
    }


async def _handle_lead_hunter_result(body: ExtensionTaskResult, session: AsyncSession):
    from app.services.facebook_action_logger import (
        fb_action_log, ACTION_REPLY,
    )

    result = await session.execute(
        select(LeadPost).where(LeadPost.id == body.lead_post_id)
    )
    lead_post = result.scalar_one_or_none()

    if not lead_post:
        raise HTTPException(status_code=404, detail=f"LeadPost {body.lead_post_id} not found")

    tracker = fb_action_log(
        ACTION_REPLY, "chrome_ext_lead_hunter",
        target_url=lead_post.post_url,
    )

    if body.success:
        lead_post.auto_reply_sent = True
        lead_post.auto_reply_sent_at = datetime.utcnow()
        lead_post.auto_reply_status = "posted"
        await tracker.finish(success=True)
        logger.info(f"🔌 ✅ Extension completed lead_hunter reply for post {lead_post.id}")
    else:
        lead_post.auto_reply_status = "failed"
        await tracker.finish(success=False, error_message=body.error)
        logger.error(f"🔌 ❌ Extension failed lead_hunter reply for post {lead_post.id}: {body.error}")

    await session.flush()

    return {
        "ok": True,
        "task_type": "lead_hunter",
        "lead_post_id": lead_post.id,
        "new_status": lead_post.auto_reply_status,
    }


@router.get("/extension/log", tags=["Chrome Extension"])
async def receive_extension_log(
    level: str = Query("info"),
    message: str = Query(...),
    reply_id: Optional[int] = Query(None),
):
    """
    התוסף שולח לוגים לבקנד לצורך debug.
    """
    log_fn = {
        "debug": logger.debug,
        "info": logger.info,
        "warn": logger.warning,
        "error": logger.error,
    }.get(level, logger.info)

    prefix = f"🔌 EXT [reply={reply_id}]" if reply_id else "🔌 EXT"
    log_fn(f"{prefix} {message}")

    return {"ok": True}
