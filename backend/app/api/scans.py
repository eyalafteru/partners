"""
PartnerCalc OS - Scans API
ניהול סריקות וקמפיינים
"""
import json
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime

from loguru import logger

from app.database import get_async_session, AsyncSessionLocal
from app.models.scan_campaign import ScanCampaign, ScanQueue, PipelineStage, PIPELINE_STAGE_LABELS
from app.models.lead import Lead
from app.scraper.apify_client import get_apify_scraper

router = APIRouter()


# ========== Auto Lead Creation Helper ==========

BLOCK_CATEGORIES = [
    "bank", "insurance", "corporation", "fintech", "government",
    "academia", "hospital", "nonprofit", "news", "ecommerce_giant", "religious"
]

async def auto_create_lead_from_scan(session: AsyncSession, item: ScanQueue):
    """
    יוצר ליד אוטומטית אחרי התאמת מחשבון מוצלחת
    """
    try:
        # Check if already exists
        existing = await session.execute(
            select(Lead).where(Lead.domain == item.domain)
        )
        if existing.scalar_one_or_none():
            return  # Already exists
        
        # Check if blacklisted
        if item.is_blacklisted or item.business_type in BLOCK_CATEGORIES:
            return  # Skip blacklisted
        
        # Check if has email and calc
        if not item.owner_email or not (item.gpt_recommended_calc_id or item.recommended_calc_id):
            return  # Missing required fields
        
        # Create lead
        lead = Lead(
            domain=item.domain,
            site_name=item.owner_org or item.domain,
            category=item.business_type,
            contact_info={
                "emails": [item.owner_email] if item.owner_email else [],
                "phones": [item.owner_phone] if item.owner_phone else [],
                "name": item.owner_org
            },
            ai_status={
                "calc_reason": item.gpt_recommended_calc_reason,
                "is_real": True,
                "auto_created": True
            },
            status="matched",
            recommended_calc_id=item.gpt_recommended_calc_id or item.recommended_calc_id,
            source_url=item.url
        )
        
        session.add(lead)
        await session.commit()
        logger.info(f"🚀 Auto-created lead for {item.domain}")
        
    except Exception as e:
        logger.error(f"Error auto-creating lead for {item.domain}: {e}")

# Global flag to stop AI analysis
AI_STOP_FLAG = {}  # {scan_id: True} means stop that scan's AI

# Global AI Queue Management
AI_QUEUE = []  # List of scan_ids waiting for AI analysis
AI_CURRENT_SCAN = None  # Currently running AI scan
AI_QUEUE_RUNNING = False  # Is the queue processor running?


# ========== Pydantic Schemas ==========

class ScanCreate(BaseModel):
    """סכמה ליצירת סריקה"""
    name: str
    keywords: List[str]
    category: Optional[str] = None
    results_per_query: int = 100  # 50, 100, 150, 200
    auto_start: bool = True  # התחל סריקה אוטומטית


class ScanResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    name: str
    keywords: Optional[List[str]]
    category: Optional[str]
    results_per_query: int
    total_urls: int
    scanned_count: int
    matched_count: int
    discarded_count: int
    contacted_count: int
    status: str
    progress_percent: float
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    # Extended stats
    whois_contacts: int = 0
    has_content: int = 0
    ai_analyzed: int = 0
    # AI progress
    ai_current_domain: Optional[str] = None
    ai_processed: int = 0
    ai_total: int = 0
    # Deep Scan & Calculator Match
    deep_scanned: int = 0
    calc_matched: int = 0
    gpt_calc_matched: int = 0
    # Deep Scan Status
    deep_scan_status: Optional[str] = None
    deep_scan_processed: int = 0
    deep_scan_total: int = 0
    deep_scan_current: Optional[str] = None
    # Calculator Match Status
    calc_match_status: Optional[str] = None
    calc_match_processed: int = 0
    calc_match_total: int = 0
    # GPT Calculator Match Status
    gpt_match_status: Optional[str] = None
    gpt_match_processed: int = 0
    gpt_match_total: int = 0
    # Rescan status
    rescan_status: Optional[str] = None
    rescan_processed: int = 0
    rescan_total: int = 0
    
    class Config:
        from_attributes = True


class ScanQueueItem(BaseModel):
    """פריט בתור סריקה"""
    id: int
    url: str
    domain: Optional[str] = None
    title: Optional[str]
    status: str
    error_message: Optional[str]
    description: Optional[str] = None
    
    # WHOIS
    owner_name: Optional[str] = None
    owner_org: Optional[str] = None
    owner_email: Optional[str] = None
    owner_phone: Optional[str] = None
    whois_is_private: Optional[bool] = False
    
    # AI
    business_type: Optional[str] = None
    business_type_reason: Optional[str] = None
    
    # Content availability
    has_content: bool = False
    html_text: Optional[str] = None
    
    # Calculator match (Ollama)
    recommended_calc_id: Optional[int] = None
    recommended_calc_name: Optional[str] = None
    recommended_calc_score: Optional[float] = None
    recommended_calc_reason: Optional[str] = None
    all_recommended_calcs: Optional[List[Dict]] = None
    
    # GPT Calculator match
    gpt_recommended_calc_id: Optional[int] = None
    gpt_recommended_calc_name: Optional[str] = None
    gpt_recommended_calc_score: Optional[float] = None
    gpt_recommended_calc_reason: Optional[str] = None
    gpt_match_duration_seconds: Optional[float] = None
    gpt_all_recommended_calcs: Optional[List[Dict]] = None
    
    # Pipeline status
    pipeline_stage: int = 0
    pipeline_stage_label: str = "ממתין"
    retry_count: int = 0
    
    class Config:
        from_attributes = True


# ========== API Endpoints ==========

@router.get("/", response_model=List[ScanResponse])
async def list_scans(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת סריקות
    """
    from urllib.parse import urlparse
    
    query = select(ScanCampaign)
    
    if status:
        query = query.where(ScanCampaign.status == status)
    
    query = query.order_by(ScanCampaign.created_at.desc()).offset(skip).limit(limit)
    result = await session.execute(query)
    campaigns = result.scalars().all()
    
    # הוספת progress_percent וספירת דומיינים יוניקים
    response = []
    for c in campaigns:
        # Count unique domains for this campaign
        queue_result = await session.execute(
            select(ScanQueue).where(ScanQueue.campaign_id == c.id)
        )
        all_items = queue_result.scalars().all()
        
        seen_domains = set()
        for item in all_items:
            try:
                parsed = urlparse(item.url or "")
                domain = parsed.netloc.replace("www.", "")
                if domain:
                    seen_domains.add(domain)
            except:
                pass
        
        unique_count = len(seen_domains)
        
        # Count items with WHOIS contact info
        whois_count = sum(1 for item in all_items if item.owner_email or item.owner_phone or item.owner_name)
        
        # Count items with content
        content_count = sum(1 for item in all_items if item.html_text)
        
        # Count items analyzed by AI
        ai_analyzed_count = sum(1 for item in all_items if item.ai_analyzed_at)
        
        # Count deep scanned items
        deep_scanned_count = sum(1 for item in all_items if item.deep_scan_status == "completed")
        
        # Count calculator matched items (Ollama)
        calc_matched_count = sum(1 for item in all_items if item.recommended_calc_id)
        
        # Count GPT calculator matched items
        gpt_calc_matched_count = sum(1 for item in all_items if item.gpt_recommended_calc_id)
        
        data = ScanResponse(
            id=c.id,
            name=c.name,
            keywords=c.keywords,
            category=c.category,
            results_per_query=c.results_per_query or 100,
            total_urls=unique_count,  # Show unique domains count
            scanned_count=c.scanned_count or 0,
            matched_count=c.matched_count or 0,
            discarded_count=c.discarded_count or 0,
            contacted_count=c.contacted_count or 0,
            status=c.status or "pending",
            progress_percent=c.progress_percent,
            created_at=c.created_at,
            started_at=c.started_at,
            completed_at=c.completed_at,
            # Extended stats
            whois_contacts=whois_count,
            has_content=content_count,
            ai_analyzed=ai_analyzed_count,
            # AI progress
            ai_current_domain=c.ai_current_domain,
            ai_processed=c.ai_processed or 0,
            ai_total=c.ai_total or 0,
            # Deep Scan & Calculator Match counts
            deep_scanned=deep_scanned_count,
            calc_matched=calc_matched_count,
            gpt_calc_matched=gpt_calc_matched_count,
            # Deep Scan Status
            deep_scan_status=c.deep_scan_status,
            deep_scan_processed=c.deep_scan_processed or 0,
            deep_scan_total=c.deep_scan_total or 0,
            deep_scan_current=c.deep_scan_current,
            # Calculator Match Status
            calc_match_status=c.calc_match_status,
            calc_match_processed=c.calc_match_processed or 0,
            calc_match_total=c.calc_match_total or 0,
            # GPT Calculator Match Status
            gpt_match_status=c.gpt_match_status,
            gpt_match_processed=c.gpt_match_processed or 0,
            gpt_match_total=c.gpt_match_total or 0,
            # Rescan status
            rescan_status=c.rescan_status,
            rescan_processed=c.rescan_processed or 0,
            rescan_total=c.rescan_total or 0
        )
        response.append(data)
    
    return response


@router.get("/domains/all")
async def get_all_domains(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    content_filter: Optional[str] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    כל הדומיינים מכל הסריקות עם פילטרים
    """
    from urllib.parse import urlparse
    
    # Get all queue items with campaign info
    query = select(ScanQueue, ScanCampaign).join(
        ScanCampaign, ScanQueue.campaign_id == ScanCampaign.id
    )
    
    # Status filter
    if status:
        query = query.where(ScanQueue.status == status)
    
    # Content/AI filter
    if content_filter == "has_content":
        query = query.where(ScanQueue.html_text != None)
    elif content_filter == "analyzed":
        query = query.where(ScanQueue.business_type != None)
    elif content_filter == "lead_site":
        query = query.where(ScanQueue.business_type == "lead_site")
    elif content_filter == "small_business":
        query = query.where(ScanQueue.business_type == "small_business")
    elif content_filter == "deep_scanned":
        query = query.where(ScanQueue.deep_scan_status == "completed")
    elif content_filter == "blacklisted":
        query = query.where(ScanQueue.is_blacklisted == 1)
    elif content_filter == "bank":
        query = query.where(ScanQueue.business_type == "bank")
    elif content_filter == "insurance":
        query = query.where(ScanQueue.business_type == "insurance")
    elif content_filter == "corporation":
        query = query.where(ScanQueue.business_type == "corporation")
    elif content_filter == "government":
        query = query.where(ScanQueue.business_type == "government")
    elif content_filter == "news":
        query = query.where(ScanQueue.business_type == "news")
    
    query = query.order_by(ScanQueue.id.desc())
    
    result = await session.execute(query)
    all_items = result.all()
    
    # Group by domain and deduplicate
    domains_map = {}
    for queue_item, campaign in all_items:
        try:
            parsed = urlparse(queue_item.url or "")
            domain = parsed.netloc.replace("www.", "")
            if not domain:
                continue
            
            if domain not in domains_map:
                domains_map[domain] = {
                    "id": queue_item.id,
                    "domain": domain,
                    "url": queue_item.url,
                    "title": queue_item.title,
                    "status": queue_item.status,
                    "campaign_name": campaign.name,
                    "keywords": campaign.keywords or [],
                    "description": queue_item.description,
                    "processed_at": queue_item.processed_at.isoformat() if queue_item.processed_at else None,
                    # WHOIS
                    "owner_name": queue_item.owner_name,
                    "owner_org": queue_item.owner_org,
                    "owner_email": queue_item.owner_email,
                    "owner_phone": queue_item.owner_phone,
                    "whois_is_private": bool(queue_item.whois_is_private),
                    # AI
                    "business_type": queue_item.business_type,
                    "business_type_reason": queue_item.business_type_reason,
                    # Content
                    "has_content": bool(queue_item.html_text),
                    "html_text": queue_item.html_text,
                    # Blacklist
                    "is_blacklisted": bool(queue_item.is_blacklisted),
                    # Deep Scan
                    "deep_scanned": queue_item.deep_scan_status == "completed"
                }
        except:
            pass
    
    # Convert to list and paginate
    domains_list = list(domains_map.values())
    total = len(domains_list)
    
    return {
        "total": total,
        "items": domains_list[skip:skip + limit]
    }


@router.post("/domains/{queue_id}/blacklist")
async def blacklist_domain(
    queue_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    הוספת דומיין לרשימה שחורה
    """
    from datetime import datetime
    
    result = await session.execute(
        select(ScanQueue).where(ScanQueue.id == queue_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="דומיין לא נמצא")
    
    item.is_blacklisted = 1
    item.blacklisted_at = datetime.utcnow()
    
    await session.commit()
    
    return {"message": "הדומיין נוסף לרשימה השחורה", "domain": item.domain}


@router.post("/domains/{queue_id}/unblacklist")
async def unblacklist_domain(
    queue_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    הסרת דומיין מרשימה שחורה
    """
    result = await session.execute(
        select(ScanQueue).where(ScanQueue.id == queue_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="דומיין לא נמצא")
    
    item.is_blacklisted = 0
    item.blacklisted_at = None
    
    await session.commit()
    
    return {"message": "הדומיין הוסר מהרשימה השחורה", "domain": item.domain}


@router.get("/domains/grouped-by-owner")
async def get_domains_grouped_by_owner(
    session: AsyncSession = Depends(get_async_session)
):
    """
    קיבוץ דומיינים לפי בעלים (WHOIS email/name)
    """
    from collections import defaultdict
    
    # Get all domains with WHOIS info
    result = await session.execute(
        select(ScanQueue).where(
            (ScanQueue.owner_email != None) | (ScanQueue.owner_name != None)
        ).where(
            ScanQueue.business_type.in_(['lead_site', 'small_business', 'content_site', 'unknown'])
        )
    )
    items = result.scalars().all()
    
    # Group by owner (prefer email, fallback to name)
    owners_map = defaultdict(lambda: {
        "owner_key": "",
        "owner_name": None,
        "owner_email": None,
        "owner_phone": None,
        "domains": [],
        "domain_count": 0
    })
    
    for item in items:
        # Create owner key (prefer email)
        owner_key = item.owner_email or item.owner_name or "unknown"
        if owner_key == "unknown" or not owner_key.strip():
            continue
            
        owner_key = owner_key.lower().strip()
        
        owners_map[owner_key]["owner_key"] = owner_key
        owners_map[owner_key]["owner_name"] = owners_map[owner_key]["owner_name"] or item.owner_name
        owners_map[owner_key]["owner_email"] = owners_map[owner_key]["owner_email"] or item.owner_email
        owners_map[owner_key]["owner_phone"] = owners_map[owner_key]["owner_phone"] or item.owner_phone
        owners_map[owner_key]["domains"].append({
            "id": item.id,
            "domain": item.domain,
            "url": item.url,
            "title": item.title,
            "business_type": item.business_type
        })
        owners_map[owner_key]["domain_count"] += 1
    
    # Convert to list and sort by domain count (descending)
    owners_list = sorted(
        owners_map.values(),
        key=lambda x: x["domain_count"],
        reverse=True
    )
    
    # Filter only owners with 2+ domains
    multi_domain_owners = [o for o in owners_list if o["domain_count"] >= 2]
    single_domain_owners = [o for o in owners_list if o["domain_count"] == 1]
    
    return {
        "multi_domain_owners": multi_domain_owners,
        "multi_domain_count": len(multi_domain_owners),
        "single_domain_owners": single_domain_owners[:50],  # Limit single owners
        "single_domain_count": len(single_domain_owners),
        "total_owners": len(owners_list)
    }


@router.get("/domains/stats")
async def get_domain_stats(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות דומיינים גלובליות
    """
    from urllib.parse import urlparse
    
    # Get all URLs from all scans
    result = await session.execute(
        select(ScanQueue.url, ScanQueue.status)
    )
    all_items = result.all()
    
    domains = {}
    for url, status in all_items:
        try:
            parsed = urlparse(url or "")
            domain = parsed.netloc.replace("www.", "")
            if domain:
                if domain not in domains:
                    domains[domain] = {"count": 0, "statuses": {}}
                domains[domain]["count"] += 1
                domains[domain]["statuses"][status] = domains[domain]["statuses"].get(status, 0) + 1
        except:
            pass
    
    # Count by status
    status_counts = {
        "pending": 0,
        "matched": 0,
        "discarded": 0,
        "error": 0
    }
    
    for domain_data in domains.values():
        for status, count in domain_data["statuses"].items():
            if status in status_counts:
                status_counts[status] += count
    
    return {
        "total_unique_domains": len(domains),
        "status_counts": status_counts,
        "top_domains": sorted(
            [(d, data["count"]) for d, data in domains.items()],
            key=lambda x: -x[1]
        )[:20]
    }


@router.get("/active")
async def get_active_scans(
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת סריקות פעילות (running)
    """
    result = await session.execute(
        select(ScanCampaign)
        .where(ScanCampaign.status == "running")
        .order_by(ScanCampaign.started_at.desc())
    )
    campaigns = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "total_urls": c.total_urls or 0,
            "scanned_count": c.scanned_count or 0,
            "matched_count": c.matched_count or 0,
            "progress_percent": c.progress_percent,
            "status": c.status
        }
        for c in campaigns
    ]


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת סריקה לפי ID
    """
    from urllib.parse import urlparse
    
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    # Count unique domains
    queue_result = await session.execute(
        select(ScanQueue).where(ScanQueue.campaign_id == scan_id)
    )
    all_items = queue_result.scalars().all()
    
    seen_domains = set()
    for item in all_items:
        try:
            parsed = urlparse(item.url or "")
            domain = parsed.netloc.replace("www.", "")
            if domain:
                seen_domains.add(domain)
        except:
            pass
    
    unique_count = len(seen_domains)
    
    return ScanResponse(
        id=campaign.id,
        name=campaign.name,
        keywords=campaign.keywords,
        category=campaign.category,
        results_per_query=campaign.results_per_query or 100,
        total_urls=unique_count,  # Show unique domains count
        scanned_count=campaign.scanned_count or 0,
        matched_count=campaign.matched_count or 0,
        discarded_count=campaign.discarded_count or 0,
        contacted_count=campaign.contacted_count or 0,
        status=campaign.status or "pending",
        progress_percent=campaign.progress_percent,
        created_at=campaign.created_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at
    )


@router.get("/{scan_id}/queue", response_model=List[ScanQueueItem])
async def get_scan_queue(
    scan_id: int,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    unique_domains: bool = True,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת תור הסריקה
    unique_domains=true יחזיר רק דומיינים יוניקים
    """
    from urllib.parse import urlparse
    
    query = select(ScanQueue).where(ScanQueue.campaign_id == scan_id)
    
    if status:
        query = query.where(ScanQueue.status == status)
    
    result = await session.execute(query)
    all_items = result.scalars().all()
    
    if unique_domains:
        # סינון כפילויות לפי דומיין
        seen_domains = set()
        unique_items = []
        
        for item in all_items:
            try:
                parsed = urlparse(item.url or "")
                domain = parsed.netloc.replace("www.", "")
                if domain and domain not in seen_domains:
                    seen_domains.add(domain)
                    unique_items.append(item)
            except:
                unique_items.append(item)
        
        # Apply pagination and add has_content + pages
        items = unique_items[skip:skip + limit]
        result_list = []
        for item in items:
            item_data = await _add_has_content_and_pages(item, session)
            result_list.append(item_data)
        return result_list
    
    items = all_items[skip:skip + limit]
    result_list = []
    for item in items:
        item_data = await _add_has_content_and_pages(item, session)
        result_list.append(item_data)
    return result_list


async def _add_has_content_and_pages(item: ScanQueue, session: AsyncSession) -> dict:
    """Add has_content field and scanned pages to queue item"""
    from app.models.scanned_page import ScannedPage
    
    data = {
        "id": item.id,
        "url": item.url,
        "domain": item.domain,
        "title": item.title,
        "status": item.status,
        "error_message": item.error_message,
        "description": item.description,
        "owner_name": item.owner_name,
        "owner_org": item.owner_org,
        "owner_email": item.owner_email,
        "owner_phone": item.owner_phone,
        "whois_is_private": bool(item.whois_is_private),
        "business_type": item.business_type,
        "business_type_reason": item.business_type_reason,
        "has_content": bool(item.html_text and len(item.html_text) > 100),
        "html_text": item.html_text,
        "deep_scan_status": item.deep_scan_status,
        "pages_scanned": item.pages_scanned or 0,
        "recommended_calc_id": item.recommended_calc_id,
        "recommended_calc_name": None,
        "recommended_calc_score": item.recommended_calc_score,
        "recommended_calc_reason": item.recommended_calc_reason,
        "all_recommended_calcs": json.loads(item.all_recommended_calcs) if item.all_recommended_calcs else None,
        # GPT Match fields
        "gpt_recommended_calc_id": item.gpt_recommended_calc_id,
        "gpt_recommended_calc_name": None,
        "gpt_recommended_calc_score": item.gpt_recommended_calc_score,
        "gpt_recommended_calc_reason": item.gpt_recommended_calc_reason,
        "gpt_match_duration_seconds": item.gpt_match_duration_seconds,
        "gpt_all_recommended_calcs": json.loads(item.gpt_all_recommended_calcs) if item.gpt_all_recommended_calcs else None,
        # Pipeline Status
        "pipeline_stage": item.pipeline_stage or 0,
        "pipeline_stage_label": item.pipeline_stage_label if hasattr(item, 'pipeline_stage_label') else PIPELINE_STAGE_LABELS.get(PipelineStage(item.pipeline_stage or 0), "ממתין"),
        "retry_count": item.retry_count or 0
    }
    
    # Get scanned pages if deep scanned
    if item.deep_scan_status == "completed":
        pages_result = await session.execute(
            select(ScannedPage).where(ScannedPage.queue_item_id == item.id)
        )
        pages = pages_result.scalars().all()
        
        data["scanned_pages"] = [
            {
                "url": p.url,
                "path": p.path,
                "page_type": p.page_type,
                "title": p.title,
                "has_contact_form": p.has_contact_form
            }
            for p in pages
        ]
    else:
        data["scanned_pages"] = []
    
    # Get calculator names for all matched calculators
    from app.models.calculator import Calculator
    
    if item.recommended_calc_id:
        calc_result = await session.execute(
            select(Calculator).where(Calculator.id == item.recommended_calc_id)
        )
        calc = calc_result.scalar_one_or_none()
        if calc:
            data["recommended_calc_name"] = calc.name
    
    # Add calc names to all_recommended_calcs
    if data.get("all_recommended_calcs"):
        calc_ids = [c["calc_id"] for c in data["all_recommended_calcs"]]
        calcs_result = await session.execute(
            select(Calculator).where(Calculator.id.in_(calc_ids))
        )
        calcs_map = {c.id: c.name for c in calcs_result.scalars().all()}
        for c in data["all_recommended_calcs"]:
            c["calc_name"] = calcs_map.get(c["calc_id"], f"מחשבון #{c['calc_id']}")
    
    # Get GPT calculator name
    if item.gpt_recommended_calc_id:
        gpt_calc_result = await session.execute(
            select(Calculator).where(Calculator.id == item.gpt_recommended_calc_id)
        )
        gpt_calc = gpt_calc_result.scalar_one_or_none()
        if gpt_calc:
            data["gpt_recommended_calc_name"] = gpt_calc.name
    
    # Add calc names to gpt_all_recommended_calcs
    if data.get("gpt_all_recommended_calcs"):
        gpt_calc_ids = [c["calc_id"] for c in data["gpt_all_recommended_calcs"]]
        gpt_calcs_result = await session.execute(
            select(Calculator).where(Calculator.id.in_(gpt_calc_ids))
        )
        gpt_calcs_map = {c.id: c.name for c in gpt_calcs_result.scalars().all()}
        for c in data["gpt_all_recommended_calcs"]:
            c["calc_name"] = gpt_calcs_map.get(c["calc_id"], f"מחשבון #{c['calc_id']}")
    
    return data


def _add_has_content(item: ScanQueue) -> dict:
    """Add has_content field to queue item (legacy - for simple cases)"""
    data = {
        "id": item.id,
        "url": item.url,
        "domain": item.domain,
        "title": item.title,
        "status": item.status,
        "error_message": item.error_message,
        "description": item.description,
        "owner_name": item.owner_name,
        "owner_org": item.owner_org,
        "owner_email": item.owner_email,
        "owner_phone": item.owner_phone,
        "whois_is_private": bool(item.whois_is_private),
        "business_type": item.business_type,
        "business_type_reason": item.business_type_reason,
        "has_content": bool(item.html_text and len(item.html_text) > 100),
        "html_text": item.html_text,
        "deep_scan_status": item.deep_scan_status,
        "pages_scanned": item.pages_scanned or 0,
        "recommended_calc_id": item.recommended_calc_id,
        "recommended_calc_score": item.recommended_calc_score,
        "recommended_calc_reason": item.recommended_calc_reason
    }
    return data


@router.post("/", response_model=ScanResponse)
async def create_scan(
    data: ScanCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת סריקה חדשה
    """
    # וידוא ערכים
    if data.results_per_query not in [50, 100, 150, 200]:
        raise HTTPException(
            status_code=400, 
            detail="results_per_query חייב להיות 50, 100, 150 או 200"
        )
    
    if not data.keywords:
        raise HTTPException(status_code=400, detail="חייב לכלול לפחות מילת מפתח אחת")
    
    # Set initial status based on auto_start
    initial_status = "running" if data.auto_start else "pending"
    
    campaign = ScanCampaign(
        name=data.name,
        keywords=data.keywords,
        category=data.category,
        results_per_query=data.results_per_query,
        status=initial_status,
        started_at=datetime.utcnow() if data.auto_start else None
    )
    
    session.add(campaign)
    await session.flush()
    await session.refresh(campaign)
    
    # Start Apify scan if auto_start is True
    if data.auto_start:
        import asyncio
        logger.info(f"🚀 Auto-starting Apify scan for campaign {campaign.id}: {campaign.name}")
        asyncio.create_task(run_apify_scan(campaign.id, campaign.keywords, campaign.results_per_query or 100))
    
    return ScanResponse(
        id=campaign.id,
        name=campaign.name,
        keywords=campaign.keywords,
        category=campaign.category,
        results_per_query=campaign.results_per_query or 100,
        total_urls=0,
        scanned_count=0,
        matched_count=0,
        discarded_count=0,
        contacted_count=0,
        status=initial_status,
        progress_percent=0.0,
        created_at=campaign.created_at,
        started_at=campaign.started_at,
        completed_at=None
    )


class ScanUpdate(BaseModel):
    """סכמה לעדכון סריקה"""
    name: Optional[str] = None
    results_per_query: Optional[int] = None


class AddKeywordsRequest(BaseModel):
    """סכמה להוספת מילות מפתח"""
    keywords: List[str]
    auto_start: bool = True


@router.put("/{scan_id}")
async def update_scan(
    scan_id: int,
    data: ScanUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון הגדרות סריקה
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if data.name:
        campaign.name = data.name
    
    if data.results_per_query and data.results_per_query in [50, 100, 150, 200]:
        campaign.results_per_query = data.results_per_query
    
    await session.commit()
    
    return {"message": "הסריקה עודכנה בהצלחה", "scan_id": scan_id}


@router.post("/{scan_id}/add-keywords")
async def add_keywords_to_scan(
    scan_id: int,
    data: AddKeywordsRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    הוספת מילות מפתח חדשות לסריקה קיימת
    מסנן כפילויות של דומיינים - רץ ב-background
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    # Update keywords list
    current_keywords = campaign.keywords or []
    new_keywords = [k.strip() for k in data.keywords if k.strip() and k.strip() not in current_keywords]
    
    if not new_keywords:
        return {
            "message": "לא נמצאו מילות מפתח חדשות להוספה",
            "new_keywords": [],
            "total_keywords": len(campaign.keywords)
        }
    
    campaign.keywords = current_keywords + new_keywords
    await session.commit()
    
    if not data.auto_start:
        return {
            "message": f"נוספו {len(new_keywords)} מילות מפתח חדשות",
            "new_keywords": new_keywords,
            "total_keywords": len(campaign.keywords)
        }
    
    # Mark as running and start in background
    campaign.status = "running"
    await session.commit()
    
    background_tasks.add_task(
        run_add_keywords_background,
        scan_id,
        new_keywords,
        campaign.results_per_query or 100
    )
    
    logger.info(f"🔄 Started background add-keywords for campaign {scan_id} with {len(new_keywords)} new keywords")
    
    return {
        "message": f"נוספו {len(new_keywords)} מילות מפתח, הסריקה התחילה ברקע",
        "new_keywords": new_keywords,
        "status": "running"
    }


async def run_add_keywords_background(scan_id: int, keywords: list, max_results: int):
    """Background task for adding keywords and scanning"""
    from urllib.parse import urlparse
    from app.database import async_session_maker
    
    async with async_session_maker() as session:
        try:
            # Get existing domains
            existing_result = await session.execute(
                select(ScanQueue.domain).where(ScanQueue.campaign_id == scan_id)
            )
            existing_domains = set(r[0] for r in existing_result.all() if r[0])
            
            logger.info(f"🔄 Background add-keywords: {len(keywords)} keywords, {len(existing_domains)} existing domains")
            
            apify = get_apify_scraper()
            new_urls_added = 0
            duplicates_skipped = 0
            
            for keyword in keywords:
                try:
                    urls = await apify.search(keyword, max_results=max_results)
                    
                    for url_data in urls:
                        url = url_data.get("url", "")
                        try:
                            parsed = urlparse(url)
                            domain = parsed.netloc.replace("www.", "")
                            
                            if domain in existing_domains:
                                duplicates_skipped += 1
                                continue
                            
                            existing_domains.add(domain)
                            
                            queue_item = ScanQueue(
                                campaign_id=scan_id,
                                url=url,
                                domain=domain,
                                title=url_data.get("title", ""),
                                description=url_data.get("description", ""),
                                google_position=url_data.get("position", 0),
                                status="pending"
                            )
                            session.add(queue_item)
                            new_urls_added += 1
                            
                        except Exception as e:
                            logger.warning(f"Error parsing URL {url}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error scanning keyword '{keyword}': {e}")
            
            await session.commit()
            
            # Update campaign
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                total_result = await session.execute(
                    select(func.count(ScanQueue.id)).where(ScanQueue.campaign_id == scan_id)
                )
                campaign.total_urls = total_result.scalar_one()
                await session.commit()
            
            logger.info(f"✅ Background add-keywords complete: {new_urls_added} new, {duplicates_skipped} duplicates")
            
            # 🚀 Auto-start pipeline for new domains
            if new_urls_added > 0:
                logger.info(f"🚀 Starting pipeline for {new_urls_added} new domains...")
                from app.services.pipeline_service import PipelineService
                pipeline_result = await PipelineService().run_pipeline(scan_id)
                logger.info(f"✅ Pipeline result: {pipeline_result}")
            else:
                if campaign:
                    campaign.status = "completed"
                    await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Background add-keywords failed: {e}")
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                campaign.status = "failed"
                await session.commit()


@router.post("/{scan_id}/rescan-keywords")
async def rescan_existing_keywords(
    scan_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקה מחדש של אותן מילות מפתח
    מסנן כפילויות - רק דומיינים חדשים יתווספו
    רץ ב-background כדי לא לחסום את השרת
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if not campaign.keywords:
        raise HTTPException(status_code=400, detail="אין מילות מפתח לסריקה")
    
    # Mark campaign as running
    campaign.status = "running"
    await session.commit()
    
    # Run in background
    background_tasks.add_task(
        run_rescan_keywords_background,
        scan_id,
        list(campaign.keywords),
        campaign.results_per_query or 100
    )
    
    logger.info(f"🔄 Started background rescan for campaign {scan_id} with {len(campaign.keywords)} keywords")
    
    return {
        "message": "סריקה מחדש התחילה ברקע",
        "status": "running",
        "keywords_count": len(campaign.keywords)
    }


async def run_rescan_keywords_background(scan_id: int, keywords: list, max_results: int):
    """Background task for rescanning keywords"""
    from urllib.parse import urlparse
    from app.database import async_session_maker
    
    async with async_session_maker() as session:
        try:
            # Get existing domains
            existing_result = await session.execute(
                select(ScanQueue.domain).where(ScanQueue.campaign_id == scan_id)
            )
            existing_domains = set(r[0] for r in existing_result.all() if r[0])
            
            logger.info(f"🔄 Background rescan: {len(keywords)} keywords, {len(existing_domains)} existing domains")
            
            apify = get_apify_scraper()
            new_urls_added = 0
            duplicates_skipped = 0
            
            for keyword in keywords:
                try:
                    urls = await apify.search(keyword, max_results=max_results)
                    
                    for url_data in urls:
                        url = url_data.get("url", "")
                        try:
                            parsed = urlparse(url)
                            domain = parsed.netloc.replace("www.", "")
                            
                            if domain in existing_domains:
                                duplicates_skipped += 1
                                continue
                            
                            existing_domains.add(domain)
                            
                            queue_item = ScanQueue(
                                campaign_id=scan_id,
                                url=url,
                                domain=domain,
                                title=url_data.get("title", ""),
                                description=url_data.get("description", ""),
                                google_position=url_data.get("position", 0),
                                status="pending"
                            )
                            session.add(queue_item)
                            new_urls_added += 1
                            
                        except Exception as e:
                            logger.warning(f"Error parsing URL {url}: {e}")
                            
                except Exception as e:
                    logger.error(f"Error scanning keyword '{keyword}': {e}")
            
            await session.commit()
            
            # Update campaign
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                total_result = await session.execute(
                    select(func.count(ScanQueue.id)).where(ScanQueue.campaign_id == scan_id)
                )
                campaign.total_urls = total_result.scalar_one()
                await session.commit()
            
            logger.info(f"✅ Background rescan complete: {new_urls_added} new, {duplicates_skipped} duplicates")
            
            # 🚀 Auto-start pipeline for new domains
            if new_urls_added > 0:
                logger.info(f"🚀 Starting pipeline for {new_urls_added} new domains...")
                from app.services.pipeline_service import PipelineService
                pipeline_result = await PipelineService().run_pipeline(scan_id)
                logger.info(f"✅ Pipeline result: {pipeline_result}")
            else:
                # No new domains, mark as completed
                if campaign:
                    campaign.status = "completed"
                    await session.commit()
            
        except Exception as e:
            logger.error(f"❌ Background rescan failed: {e}")
            # Mark as failed
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                campaign.status = "failed"
                await session.commit()


@router.post("/{scan_id}/start")
async def start_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    התחלת סריקה
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="הסריקה כבר רצה")
    
    campaign.status = "running"
    campaign.started_at = datetime.utcnow()
    
    await session.flush()
    
    # Run Apify scan directly (without Celery for now)
    import asyncio
    asyncio.create_task(run_apify_scan(scan_id, campaign.keywords, campaign.results_per_query or 100))
    
    return {"message": "הסריקה התחילה", "scan_id": scan_id}


async def run_apify_scan(scan_id: int, keywords: list, results_per_query: int):
    """Run Apify scan in background"""
    from loguru import logger
    from urllib.parse import urlparse
    
    logger.info(f"Starting Apify scan for campaign {scan_id}")
    
    try:
        apify = get_apify_scraper()
        all_results = []
        
        for keyword in keywords:
            try:
                logger.info(f"Searching: {keyword}")
                results = await apify.search(keyword, results_per_query)
                all_results.extend(results)
                logger.info(f"Found {len(results)} results for '{keyword}'")
            except Exception as e:
                logger.error(f"Apify search failed for '{keyword}': {e}")
        
        # Save to database
        async with AsyncSessionLocal() as session:
            # Get ALL existing domains from ALL scan queues (global uniqueness)
            existing_result = await session.execute(
                select(ScanQueue.url)
            )
            existing_urls = existing_result.scalars().all()
            
            existing_domains = set()
            for url in existing_urls:
                try:
                    parsed = urlparse(url or "")
                    domain = parsed.netloc.replace("www.", "")
                    if domain:
                        existing_domains.add(domain)
                except:
                    pass
            
            logger.info(f"Found {len(existing_domains)} existing domains in database")
            
            # Update campaign
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            
            if campaign:
                # Deduplicate by domain (including global check)
                seen_domains = set()
                unique_results = []
                skipped_existing = 0
                
                for r in all_results:
                    domain = r.get('domain', '')
                    if not domain:
                        continue
                    
                    # Skip if already exists in database (from other scans)
                    if domain in existing_domains:
                        skipped_existing += 1
                        continue
                    
                    # Skip if already in this batch
                    if domain in seen_domains:
                        continue
                    
                    seen_domains.add(domain)
                    unique_results.append(r)
                
                logger.info(f"Skipped {skipped_existing} domains that already exist in other scans")
                
                # Add to queue
                for r in unique_results:
                    queue_item = ScanQueue(
                        campaign_id=scan_id,
                        url=r.get('url', ''),
                        title=r.get('title', ''),
                        description=r.get('description', ''),
                        google_position=r.get('position'),
                        status='pending'
                    )
                    session.add(queue_item)
                
                campaign.total_urls = len(unique_results)
                campaign.status = 'completed' if unique_results else 'failed'
                campaign.completed_at = datetime.utcnow()
                
                await session.commit()
                logger.info(f"Scan {scan_id} completed: {len(unique_results)} new unique URLs found")
                
    except Exception as e:
        logger.error(f"Scan {scan_id} failed: {e}")
        
        # Update status to failed
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = result.scalar_one_or_none()
            if campaign:
                campaign.status = 'failed'
                await session.commit()


@router.post("/{scan_id}/analyze")
async def start_analysis(
    scan_id: int,
    batch_size: int = 10,
    use_browser: bool = True,
    continuous: bool = True,  # המשך אוטומטי לכל האתרים
    session: AsyncSession = Depends(get_async_session)
):
    """
    התחלת ניתוח HTML של האתרים שנאספו
    
    Args:
        batch_size: כמה אתרים לנתח בכל batch
        use_browser: True = Puppeteer (עוקף CF), False = Cheerio (מהיר)
        continuous: True = המשך אוטומטי עד סיום כל האתרים
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    # Count total pending
    from sqlalchemy import func as sql_func
    count_result = await session.execute(
        select(sql_func.count(ScanQueue.id))
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.status == "pending")
    )
    total_pending = count_result.scalar() or 0
    
    if total_pending == 0:
        return {"message": "אין אתרים לניתוח", "analyzed": 0}
    
    # Start analysis in background
    import asyncio
    asyncio.create_task(run_continuous_analysis(scan_id, batch_size, use_browser, continuous))
    
    return {
        "message": f"מתחיל ניתוח של {total_pending} אתרים",
        "scan_id": scan_id,
        "total_pending": total_pending,
        "batch_size": batch_size,
        "continuous": continuous
    }


async def run_continuous_analysis(scan_id: int, batch_size: int, use_browser: bool, continuous: bool):
    """ניתוח רציף של כל האתרים"""
    from loguru import logger
    import asyncio
    
    logger.info(f"Starting continuous analysis for scan {scan_id}")
    
    while True:
        # Get next batch of pending URLs
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ScanQueue)
                .where(ScanQueue.campaign_id == scan_id)
                .where(ScanQueue.status == "pending")
                .limit(batch_size)
            )
            pending_items = result.scalars().all()
            
            if not pending_items:
                logger.info(f"No more pending URLs for scan {scan_id}")
                break
            
            queue_ids = [item.id for item in pending_items]
        
        # Analyze this batch
        await run_html_analysis(scan_id, queue_ids, use_browser)
        
        if not continuous:
            break
        
        # Small delay between batches
        await asyncio.sleep(1)
    
    logger.info(f"Continuous analysis complete for scan {scan_id}")


async def run_html_analysis(scan_id: int, queue_ids: List[int], use_browser: bool):
    """ניתוח HTML + WHOIS ברקע"""
    from app.scraper.smart_scraper import get_smart_scraper
    from app.scraper.whois_lookup import get_whois_lookup
    from urllib.parse import urlparse
    from loguru import logger
    
    logger.info(f"Starting HTML + WHOIS analysis for scan {scan_id}, {len(queue_ids)} URLs")
    
    try:
        async with AsyncSessionLocal() as session:
            # Get URLs to analyze
            result = await session.execute(
                select(ScanQueue).where(ScanQueue.id.in_(queue_ids))
            )
            items = result.scalars().all()
            
            urls = [item.url for item in items]
            url_to_item = {item.url: item for item in items}
            
            # Update status to analyzing
            for item in items:
                item.status = "analyzing"
            await session.commit()
            
            # Scrape with SmartScraper (local first, Zenrows as fallback)
            scraper = get_smart_scraper()
            whois_client = get_whois_lookup()
            
            results = await scraper.scrape_batch(urls, delay=1.0, max_concurrent=3)
            
            # Update database with results
            for scrape_result in results:
                url = scrape_result.get("url", "")
                item = url_to_item.get(url)
                
                if item:
                    # Extract domain for WHOIS
                    try:
                        parsed = urlparse(url)
                        domain = parsed.netloc.replace("www.", "")
                        item.domain = domain
                        
                        # WHOIS lookup
                        logger.info(f"WHOIS lookup for {domain}")
                        whois_data = await whois_client.lookup(domain)
                        
                        # Store WHOIS data
                        item.owner_name = whois_data.get("registrant_name")
                        item.owner_org = whois_data.get("registrant_org")
                        item.owner_email = whois_data.get("registrant_email")
                        item.owner_phone = whois_data.get("registrant_phone")
                        item.owner_address = whois_data.get("address")
                        item.owner_city = whois_data.get("city")
                        item.owner_country = whois_data.get("country")
                        item.registrar = whois_data.get("registrar")
                        item.whois_is_private = whois_data.get("is_private", False)
                        item.whois_checked_at = datetime.utcnow()
                        
                        # Handle dates
                        if whois_data.get("creation_date"):
                            try:
                                from dateutil import parser as date_parser
                                item.domain_created = date_parser.parse(whois_data["creation_date"])
                            except:
                                pass
                        if whois_data.get("expiration_date"):
                            try:
                                from dateutil import parser as date_parser
                                item.domain_expires = date_parser.parse(whois_data["expiration_date"])
                            except:
                                pass
                        
                        item.whois_data = whois_data  # Full JSON backup
                        
                    except Exception as e:
                        logger.warning(f"WHOIS lookup failed for {url}: {e}")
                    
                    if scrape_result.get("error"):
                        item.status = "error"
                        item.error_message = scrape_result["error"]
                    else:
                        # Check if has contact info (from scraping OR from WHOIS)
                        has_page_contact = bool(scrape_result.get("emails") or scrape_result.get("phones"))
                        has_whois_contact = bool(item.owner_email and not item.whois_is_private)
                        has_contact = has_page_contact or has_whois_contact
                        
                        if has_contact:
                            item.status = "matched"
                            # TODO: Create lead from this
                        else:
                            item.status = "discarded"
                        
                        # Store scraped data
                        item.emails_found = scrape_result.get("emails", [])
                        item.phones_found = scrape_result.get("phones", [])
                        
                        # Store HTML content for AI analysis
                        if scrape_result.get("html"):
                            item.html_body = scrape_result["html"][:50000]  # Limit to 50KB
                        if scrape_result.get("inner_text"):
                            item.html_text = scrape_result["inner_text"][:10000]  # Limit to 10KB
                        
                        # Store navigation and meta data
                        if scrape_result.get("nav_links"):
                            import json
                            item.nav_links = json.dumps(scrape_result["nav_links"], ensure_ascii=False)
                        if scrape_result.get("title"):
                            item.meta_title = scrape_result["title"][:500]
                        if scrape_result.get("meta_description"):
                            item.meta_description = scrape_result["meta_description"][:1000]
                        if scrape_result.get("meta_keywords"):
                            item.meta_keywords = scrape_result["meta_keywords"][:500]
                        if scrape_result.get("has_menu_calculator") is not None:
                            item.has_menu_calculator = 1 if scrape_result["has_menu_calculator"] else 0
                        
                        # Store scraped data in description field
                        contact_info = []
                        if scrape_result.get("emails"):
                            contact_info.append(f"Emails: {', '.join(scrape_result['emails'])}")
                        if scrape_result.get("phones"):
                            contact_info.append(f"Phones: {', '.join(scrape_result['phones'])}")
                        if item.owner_email and not item.whois_is_private:
                            contact_info.append(f"WHOIS Email: {item.owner_email}")
                        
                        item.description = "\n".join(contact_info) if contact_info else ""
                    
                    item.processed_at = datetime.utcnow()
            
            await session.commit()
            
            # Update campaign counters
            campaign_result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            
            if campaign:
                # Count statuses
                count_result = await session.execute(
                    select(
                        func.count(ScanQueue.id).filter(ScanQueue.status == "matched"),
                        func.count(ScanQueue.id).filter(ScanQueue.status == "discarded"),
                        func.count(ScanQueue.id).filter(ScanQueue.status.in_(["matched", "discarded", "error"]))
                    ).where(ScanQueue.campaign_id == scan_id)
                )
                matched, discarded, scanned = count_result.one()
                
                campaign.matched_count = matched
                campaign.discarded_count = discarded
                campaign.scanned_count = scanned
                
                await session.commit()
            
            logger.info(f"Analysis complete for scan {scan_id}")
            
    except Exception as e:
        logger.error(f"HTML analysis failed for scan {scan_id}: {e}")


@router.post("/{scan_id}/pause")
async def pause_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    השהיית סריקה
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if campaign.status != "running":
        raise HTTPException(status_code=400, detail="הסריקה לא רצה")
    
    campaign.status = "paused"
    await session.flush()
    
    return {"message": "הסריקה הושהתה", "scan_id": scan_id}


@router.post("/{scan_id}/stop")
async def stop_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עצירת סריקה
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    campaign.status = "completed"
    campaign.completed_at = datetime.utcnow()
    
    await session.flush()
    
    return {"message": "הסריקה נעצרה", "scan_id": scan_id}


@router.post("/{scan_id}/retry")
async def retry_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    נסה שוב סריקה שנכשלה
    """
    from loguru import logger
    
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if campaign.status != "failed":
        raise HTTPException(status_code=400, detail="ניתן לנסות שוב רק סריקות שנכשלו")
    
    # Reset status to running
    campaign.status = "running"
    campaign.total_urls = 0
    campaign.scanned_count = 0
    await session.commit()
    
    # Start the scan again
    logger.info(f"🔄 Retrying scan {scan_id}: {campaign.name}")
    
    import asyncio
    asyncio.create_task(run_apify_scan(scan_id, campaign.keywords, campaign.results_per_query))
    
    return {"message": "הסריקה הופעלה מחדש", "scan_id": scan_id, "status": "running"}


@router.post("/{scan_id}/rescan-no-content")
async def rescan_sites_without_content(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקה מחדש של אתרים שאין להם תוכן
    """
    from loguru import logger
    
    # Get items without content (None or too short)
    from sqlalchemy import or_, func
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(or_(
            ScanQueue.html_text == None,
            func.length(ScanQueue.html_text) < 100
        ))
    )
    items_without_content = result.scalars().all()
    
    total = len(items_without_content)
    if total == 0:
        return {"message": "כל האתרים כבר נסרקו", "rescan_count": 0}
    
    logger.info(f"Rescan {total} sites without content for campaign {scan_id}")
    
    # Update campaign status
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.rescan_status = "running"
        campaign.rescan_processed = 0
        campaign.rescan_total = total
        await session.commit()
    
    # Get queue IDs to rescan
    queue_ids = [item.id for item in items_without_content]
    
    # Start background task using existing function
    import asyncio
    asyncio.create_task(rescan_items_without_content(scan_id, queue_ids))
    
    return {"message": f"מתחיל סריקה מחדש של {total} אתרים", "rescan_count": total}


@router.post("/{scan_id}/rescan-all-for-navigation")
async def rescan_all_for_navigation(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקה מחדש של כל האתרים - מביא תוכן + navigation + meta
    """
    from loguru import logger
    
    # Get ALL items (not just with content)
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
    )
    all_items = result.scalars().all()
    
    total = len(all_items)
    if total == 0:
        return {"message": "אין אתרים לסריקה", "rescan_count": 0}
    
    # Update campaign status
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if not campaign:
        return {"message": "סריקה לא נמצאה", "rescan_count": 0}
    
    campaign.rescan_status = "running"
    campaign.rescan_processed = 0
    campaign.rescan_total = total
    await session.commit()
    
    logger.info(f"🔄 Starting navigation rescan for {total} sites in scan {scan_id}")
    
    # Start background task
    import asyncio
    asyncio.create_task(run_navigation_rescan(scan_id, [item.id for item in all_items]))
    
    return {
        "message": f"מתחיל סריקה מלאה ל-{total} אתרים (תוכן + navigation)",
        "rescan_count": total
    }


async def run_navigation_rescan(scan_id: int, item_ids: list):
    """Background task - סריקה מלאה: תוכן + navigation + meta"""
    from app.scraper.smart_scraper import get_smart_scraper
    from app.database import AsyncSessionLocal
    from loguru import logger
    import json
    
    scraper = get_smart_scraper()
    
    async with AsyncSessionLocal() as session:
        for idx, item_id in enumerate(item_ids, 1):
            try:
                # Update progress
                campaign_result = await session.execute(
                    select(ScanCampaign).where(ScanCampaign.id == scan_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    campaign.rescan_processed = idx
                    campaign.ai_current_domain = f"סורק תוכן + navigation... ({idx}/{len(item_ids)})"
                    await session.commit()
                
                # Get item
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                logger.info(f"🔄 Full rescan: {item.url}")
                
                # Scrape - get everything!
                scrape_result = await scraper.scrape(item.url)
                
                if scrape_result and not scrape_result.get("error"):
                    # Update HTML content
                    if scrape_result.get("html"):
                        item.html_body = scrape_result["html"][:50000]
                    if scrape_result.get("inner_text"):
                        item.html_text = scrape_result["inner_text"][:15000]
                    if scrape_result.get("title"):
                        item.title = scrape_result["title"][:500]
                        item.meta_title = scrape_result["title"][:500]
                    
                    # Update navigation links
                    if scrape_result.get("nav_links"):
                        item.nav_links = json.dumps(scrape_result["nav_links"], ensure_ascii=False)
                    
                    # Update meta data
                    if scrape_result.get("meta_description"):
                        item.meta_description = scrape_result["meta_description"][:1000]
                    if scrape_result.get("meta_keywords"):
                        item.meta_keywords = scrape_result["meta_keywords"][:500]
                    if scrape_result.get("has_menu_calculator") is not None:
                        item.has_menu_calculator = 1 if scrape_result["has_menu_calculator"] else 0
                    
                    await session.commit()
                    logger.info(f"✅ Full update for {item.url} - content + navigation")
                
                # Small delay
                import asyncio
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error rescanning {item_id}: {e}")
        
        # Mark as completed
        campaign_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.rescan_status = None  # Reset to None instead of "completed"
            campaign.rescan_processed = 0
            campaign.rescan_total = 0
            campaign.ai_current_domain = None
            await session.commit()
        
        logger.info(f"✅ Navigation rescan completed for scan {scan_id}")
    
    logger.info(f"🔄 Rescanning {total} sites without content for scan {scan_id}")
    
    # Update campaign - don't change status, just update ai_current_domain for progress
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.ai_current_domain = f"סורק תוכן מחדש 0/{total}"
        await session.commit()
    
    # Start background task
    import asyncio
    asyncio.create_task(rescan_items_without_content(scan_id, [item.id for item in items_without_content]))
    
    return {
        "message": f"מתחיל סריקה מחדש של {total} אתרים ללא תוכן",
        "rescan_count": total
    }


async def rescan_items_without_content(scan_id: int, item_ids: list, force_browser: bool = True):
    """סריקה מחדש של אתרים ללא תוכן ברקע - עם דפדפן כברירת מחדל"""
    from app.scraper.smart_scraper import get_smart_scraper
    from app.scraper.whois_lookup import get_whois_lookup
    from loguru import logger
    
    scraper = get_smart_scraper()
    whois = get_whois_lookup()
    logger.info(f"Starting rescan for {len(item_ids)} items with force_browser={force_browser}")
    
    async with AsyncSessionLocal() as session:
        total = len(item_ids)
        success_count = 0
        
        for idx, item_id in enumerate(item_ids):
            try:
                # Get item
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                logger.info(f"🔄 [{idx+1}/{total}] Rescanning: {item.url}")
                
                # Update campaign progress
                campaign_result = await session.execute(
                    select(ScanCampaign).where(ScanCampaign.id == scan_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    campaign.ai_current_domain = f"סורק מחדש {idx+1}/{total}"
                    await session.commit()
                
                # Scrape content - with browser for JS sites
                scrape_result = await scraper.scrape(item.url, force_browser=force_browser)
                
                if scrape_result and not scrape_result.get("error"):
                    item.html_body = scrape_result.get("html", "")[:50000]
                    item.html_text = scrape_result.get("inner_text", "")[:15000]
                    item.title = scrape_result.get("title", item.title)
                    
                    # Store navigation and meta data
                    if scrape_result.get("nav_links"):
                        import json
                        item.nav_links = json.dumps(scrape_result["nav_links"], ensure_ascii=False)
                    if scrape_result.get("meta_description"):
                        item.meta_description = scrape_result["meta_description"][:1000]
                    if scrape_result.get("meta_keywords"):
                        item.meta_keywords = scrape_result["meta_keywords"][:500]
                    if scrape_result.get("has_menu_calculator") is not None:
                        item.has_menu_calculator = 1 if scrape_result["has_menu_calculator"] else 0
                    
                    # Update emails/phones if found
                    if scrape_result.get("emails"):
                        item.emails_found = scrape_result["emails"]
                    if scrape_result.get("phones"):
                        item.phones_found = scrape_result["phones"]
                    
                    item.status = "matched"
                    success_count += 1
                    logger.info(f"✅ Got content for {item.domain}")
                else:
                    logger.warning(f"❌ Still no content for {item.domain}")
                
                await session.commit()
                
                # Small delay between requests
                import asyncio
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error rescanning {item_id}: {e}")
        
        # Mark as complete - don't change status
        campaign_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.ai_current_domain = f"סריקת תוכן הושלמה ✅ ({success_count}/{total})"
            await session.commit()
        
        logger.info(f"✅ Rescan complete: {success_count}/{total} sites got content")


@router.delete("/{scan_id}")
async def delete_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת סריקה
    """
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="סריקה לא נמצאה")
    
    if campaign.status == "running":
        raise HTTPException(status_code=400, detail="לא ניתן למחוק סריקה רצה")
    
    # מחיקת פריטי התור
    await session.execute(
        select(ScanQueue).where(ScanQueue.campaign_id == scan_id)
    )
    
    await session.delete(campaign)
    
    return {"message": f"סריקה {scan_id} נמחקה בהצלחה"}


# ========== WHOIS Lookup ==========

@router.get("/whois/{domain}")
async def whois_lookup(domain: str):
    """
    חיפוש פרטי WHOIS של דומיין
    """
    from app.scraper.whois_lookup import get_whois_lookup
    
    whois = get_whois_lookup()
    result = await whois.lookup(domain)
    
    return result


@router.post("/domains/enrich-whois")
async def enrich_domains_whois(
    limit: int = Query(10, description="מספר דומיינים להעשרה"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    העשרת דומיינים בפרטי WHOIS - שומר בשדות נפרדים
    """
    from app.scraper.whois_lookup import get_whois_lookup
    from urllib.parse import urlparse
    
    # Get domains without WHOIS data
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.whois_checked_at == None)
        .where(ScanQueue.status.in_(["matched", "pending"]))
        .limit(limit)
    )
    items = result.scalars().all()
    
    if not items:
        return {"message": "אין דומיינים להעשרה", "enriched": 0}
    
    whois_client = get_whois_lookup()
    enriched = 0
    private_count = 0
    
    for item in items:
        try:
            domain = urlparse(item.url).netloc.replace("www.", "")
            item.domain = domain
            
            whois_result = await whois_client.lookup(domain)
            
            # שמירה בשדות נפרדים
            item.owner_name = whois_result.get("registrant_name")
            item.owner_org = whois_result.get("registrant_org")
            item.owner_email = whois_result.get("registrant_email")
            item.owner_phone = whois_result.get("registrant_phone")
            item.owner_address = whois_result.get("address")
            item.owner_city = whois_result.get("city")
            item.owner_country = whois_result.get("country")
            
            item.domain_created = whois_result.get("creation_date")
            item.domain_expires = whois_result.get("expiration_date")
            item.registrar = whois_result.get("registrar")
            
            item.whois_is_private = 1 if whois_result.get("is_private") else 0
            item.whois_data = whois_result  # גיבוי מלא
            item.whois_checked_at = datetime.utcnow()
            
            if whois_result.get("is_private"):
                private_count += 1
            
            enriched += 1
            
        except Exception as e:
            logger.error(f"WHOIS enrichment failed for {item.url}: {e}")
            item.whois_checked_at = datetime.utcnow()  # סימון שנבדק גם אם נכשל
    
    await session.commit()
    
    return {
        "message": f"הועשרו {enriched} דומיינים ({private_count} פרטיים)",
        "enriched": enriched,
        "private_count": private_count
    }


# ========== AI Business Type Analysis ==========

@router.post("/{scan_id}/analyze-business-type")
async def analyze_business_type(
    scan_id: int,
    batch_size: int = Query(10, description="מספר אתרים לניתוח בכל batch"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    ניתוח סוג העסק באמצעות AI (DictaLM)
    מסווג: lead_site, small_business, content_site, corporation, bank, insurance, fintech, unknown
    מוסיף לתור גלובלי - רק סריקה אחת רצה בכל רגע נתון!
    """
    global AI_QUEUE, AI_CURRENT_SCAN, AI_QUEUE_RUNNING
    from loguru import logger
    
    # Count total items to analyze
    count_result = await session.execute(
        select(func.count(ScanQueue.id))
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.ai_analyzed_at == None)
        .where(ScanQueue.html_text != None)  # Only items with content
    )
    total_to_analyze = count_result.scalar() or 0
    
    if total_to_analyze == 0:
        return {"message": "אין אתרים לניתוח AI", "analyzed": 0, "total": 0}
    
    # Check if already in queue or running
    if scan_id in AI_QUEUE:
        position = AI_QUEUE.index(scan_id) + 1
        return {"message": f"הסריקה כבר בתור במיקום {position}", "queue_position": position}
    
    if AI_CURRENT_SCAN == scan_id:
        return {"message": "הסריקה כבר רצה", "status": "running"}
    
    # Add to queue
    AI_QUEUE.append(scan_id)
    position = len(AI_QUEUE)
    
    logger.info(f"📋 Added scan {scan_id} to AI queue at position {position}")
    
    # Update campaign status
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.ai_current_domain = f"בתור ({position})" if position > 1 else "ממתין..."
        campaign.ai_total = total_to_analyze
        campaign.ai_processed = 0
        await session.commit()
    
    # Start queue processor if not running
    if not AI_QUEUE_RUNNING:
        import asyncio
        asyncio.create_task(process_ai_queue())
    
    return {
        "message": f"נוסף לתור AI במיקום {position} ({total_to_analyze} אתרים)",
        "queue_position": position,
        "total": total_to_analyze,
        "queue_length": len(AI_QUEUE)
    }


async def process_ai_queue():
    """מעבד את תור ה-AI - סריקה אחת בכל פעם"""
    global AI_QUEUE, AI_CURRENT_SCAN, AI_QUEUE_RUNNING
    from loguru import logger
    
    if AI_QUEUE_RUNNING:
        return
    
    AI_QUEUE_RUNNING = True
    logger.info("🚀 AI Queue processor started")
    
    try:
        while AI_QUEUE:
            # Get next scan from queue
            scan_id = AI_QUEUE.pop(0)
            AI_CURRENT_SCAN = scan_id
            
            logger.info(f"🤖 Processing scan {scan_id} from queue ({len(AI_QUEUE)} remaining)")
            
            # Update queue positions for remaining items
            async with AsyncSessionLocal() as session:
                for idx, queued_id in enumerate(AI_QUEUE):
                    result = await session.execute(
                        select(ScanCampaign).where(ScanCampaign.id == queued_id)
                    )
                    campaign = result.scalar_one_or_none()
                    if campaign:
                        campaign.ai_current_domain = f"בתור ({idx + 1})"
                await session.commit()
            
            # Run the actual AI analysis
            await run_ai_business_analysis_all(scan_id)
            
            AI_CURRENT_SCAN = None
            
    finally:
        AI_QUEUE_RUNNING = False
        AI_CURRENT_SCAN = None
        logger.info("✅ AI Queue processor finished")


async def run_ai_business_analysis_all(scan_id: int):
    """ניתוח AI ברקע - כל האתרים עד הסוף! (GPT)"""
    from app.ai.openai_client import get_openai_client
    from loguru import logger
    from datetime import datetime
    import json
    import re
    
    gpt = get_openai_client()
    
    # System prompt
    system_prompt = """אתה מומחה בזיהוי סוגי עסקים. נתח את הנתונים וסווג את האתר.

🎯 המטרה: לזהות אתרים של עסקים קטנים/אתרי לידים שנוכל ליצור איתם שיתוף פעולה.

📊 קטגוריות:
1. lead_site - אתר לידים / שיווק שותפים 🎯
2. small_business - עסק קטן / יועץ 💼
3. content_site - אתר תוכן / בלוג 📰
4. corporation - תאגיד גדול / חברת אשראי 🏢
5. bank - בנק 🏦
6. insurance - חברת ביטוח 🛡️
7. fintech - פינטק / סטארטאפ 🚀
8. unknown - לא ידוע ❓

החזר JSON בלבד:
{"type": "lead_site/small_business/content_site/corporation/bank/insurance/fintech/unknown", "reason": "הסבר קצר"}"""
    
    try:
        async with AsyncSessionLocal() as session:
            # Get ALL items that need analysis
            result = await session.execute(
                select(ScanQueue)
                .where(ScanQueue.campaign_id == scan_id)
                .where(ScanQueue.ai_analyzed_at == None)
                .where(ScanQueue.html_text != None)
            )
            all_items = result.scalars().all()
            
            total_items = len(all_items)
            if total_items == 0:
                logger.info(f"No items to analyze for scan {scan_id}")
                return
            
            # Update campaign with total
            campaign_result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            if campaign:
                campaign.ai_total = total_items
                campaign.ai_processed = 0
                campaign.ai_current_domain = "מתחיל..."
                await session.commit()
            
            logger.info(f"🤖 Starting AI analysis for ALL {total_items} sites in scan {scan_id}")
            
            # Clear stop flag at start
            global AI_STOP_FLAG
            AI_STOP_FLAG[scan_id] = False
            
            for idx, item in enumerate(all_items):
                # Check stop flag
                if AI_STOP_FLAG.get(scan_id, False):
                    logger.info(f"🛑 AI analysis stopped by user for scan {scan_id} at {idx}/{total_items}")
                    if campaign:
                        campaign.ai_current_domain = "נעצר ⏹️"
                        await session.commit()
                    return
                
                try:
                    # Update progress
                    if campaign:
                        campaign.ai_current_domain = item.domain or "..."
                        campaign.ai_processed = idx + 1
                        await session.commit()
                    
                    # Build context
                    context_parts = [f"🌐 דומיין: {item.domain}"]
                    if item.title:
                        context_parts.append(f"📌 כותרת: {item.title}")
                    if item.owner_email:
                        context_parts.append(f"✉️ WHOIS מייל: {item.owner_email}")
                    if item.owner_org:
                        context_parts.append(f"🏢 WHOIS ארגון: {item.owner_org}")
                    if item.html_text:
                        context_parts.append(f"\n📄 תוכן (5000 תווים):\n{item.html_text[:5000]}")
                    
                    user_prompt = "\n".join(context_parts)
                    
                    logger.info(f"🤖 [{idx+1}/{total_items}] Analyzing with GPT: {item.domain}")
                    
                    # Call GPT API
                    response, duration = await gpt.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.3,
                        max_tokens=300
                    )
                    
                    # Parse JSON response (GPT returns clean JSON)
                    try:
                        parsed = json.loads(response)
                        item.business_type = parsed.get("type", "unknown")
                        item.business_type_reason = parsed.get("reason", "")
                    except:
                        # Fallback: try to extract JSON from response
                        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
                        if json_match:
                            try:
                                parsed = json.loads(json_match.group())
                                item.business_type = parsed.get("type", "unknown")
                                item.business_type_reason = parsed.get("reason", "")
                            except:
                                item.business_type = "unknown"
                                item.business_type_reason = response[:500]
                        else:
                            item.business_type = "unknown"
                            item.business_type_reason = response[:500]
                    
                    item.ai_analyzed_at = datetime.utcnow()
                    
                    # Auto-blacklist blocked categories
                    KEEP_CATEGORIES = ["lead_site", "small_business"]
                    if item.business_type and item.business_type not in KEEP_CATEGORIES:
                        item.is_blacklisted = 1
                    else:
                        item.is_blacklisted = 0
                    
                    await session.commit()
                    
                    emoji = {"lead_site": "🎯", "small_business": "💼", "content_site": "📰", 
                             "bank": "🏦", "insurance": "🛡️", "corporation": "🏢", "fintech": "🚀",
                             "government": "🏛️", "academia": "🎓", "hospital": "🏥", "news": "📰"}.get(item.business_type, "❓")
                    blocked = "🚫" if item.is_blacklisted else "✅"
                    logger.info(f"   {emoji} {blocked} Result: {item.business_type}")
                    
                except Exception as e:
                    logger.error(f"❌ Error analyzing {item.domain}: {e}")
                    item.business_type = "error"
                    item.business_type_reason = str(e)[:500]
                    item.ai_analyzed_at = datetime.utcnow()
                    item.is_blacklisted = 1  # Error = blocked
                    await session.commit()
            
            # Done!
            if campaign:
                campaign.ai_current_domain = "✅ הושלם!"
                campaign.ai_processed = total_items
                await session.commit()
            
            logger.info(f"✅ AI analysis COMPLETE for {total_items} sites!")
            
    except Exception as e:
        logger.error(f"AI batch analysis failed: {e}")


async def run_ai_business_analysis(scan_id: int, queue_ids: List[int]):
    """ניתוח AI ברקע - רשימה ספציפית (GPT)"""
    from app.ai.openai_client import get_openai_client
    from loguru import logger
    
    total_items = len(queue_ids)
    logger.info(f"🤖 Starting AI business analysis with GPT for {total_items} sites")
    
    gpt = get_openai_client()
    
    # System prompt for business classification
    system_prompt = """אתה מומחה בזיהוי סוגי עסקים. נתח את הנתונים וסווג את האתר.

🎯 המטרה: לזהות אתרים של עסקים קטנים/אתרי לידים שנוכל ליצור איתם שיתוף פעולה.
לסנן: בנקים, ביטוח, תאגידים גדולים, חברות אשראי.

📊 קטגוריות (בחר אחת):

1. **lead_site** - אתר לידים / שיווק שותפים 🎯
   סימנים: טפסי לידים, "השאר פרטים", "קבל הצעת מחיר", מספרי טלפון בולטים, CTA לפעולה
   WHOIS: לרוב אדם פרטי או חברה קטנה כבעלים
   דוגמאות: loan-israel.co.il, halvaot.co.il, mashkanta4u.co.il

2. **small_business** - עסק קטן / יועץ / משווק 💼
   סימנים: שם אדם בעמוד, "אודות", ניסיון אישי, תעודות, המלצות
   WHOIS: בד"כ אדם פרטי כבעלים
   דוגמאות: credit.as-invest.co.il, yoetzpinance.co.il

3. **content_site** - אתר תוכן / בלוג / מגזין 📰
   סימנים: מאמרים, תאריכי פרסום, כותבים שונים, אין טפסי לידים
   דוגמאות: calcalist.co.il, themarker.com (אבל אלה גדולים מדי)

4. **corporation** - תאגיד גדול / חברת אשראי 🏢
   סימנים: חברה ציבורית, מניות בבורסה, אלפי עובדים
   דוגמאות: max.co.il, isracard.co.il, cal-online.co.il, leumi-card.co.il, paybox, pepper

5. **bank** - בנק 🏦
   סימנים: רישיון בנקאי, סניפים, שירותי בנקאות מלאים
   דוגמאות: bankhapoalim.co.il, leumi.co.il, discountbank.co.il, mizrahi-tefahot.co.il, bankjerusalem.co.il

6. **insurance** - חברת ביטוח 🛡️
   סימנים: פוליסות ביטוח, תביעות, סוכני ביטוח
   דוגמאות: harel.co.il, migdal.co.il, clal-ins.co.il, fnx.co.il, menora.co.il

7. **fintech** - פינטק / סטארטאפ פיננסי 🚀
   סימנים: אפליקציה, טכנולוגיה חדשנית, גיוסי הון
   דוגמאות: pepper.co.il, bit.co.il, paybox.co.il

8. **unknown** - לא ניתן לזהות ❓

🔍 סימנים לזיהוי עסק קטן/אתר לידים (lead_site/small_business):
- WHOIS: בעלים פרטי (לא חברה גדולה)
- מייל אישי (gmail, outlook) או מייל עם שם אדם
- טלפון נייד (05X) או טלפון אחד בלבד
- טופס "השאר פרטים", "צור קשר", "קבל הצעה"
- מילים: "יועץ", "מומחה", "ניסיון של X שנים", "עזרתי ל", "אני מתמחה"
- אין: "בע"מ", "מניות", "דוח שנתי", "סניפים"

🚫 סימנים לתאגיד גדול (לסנן):
- שם חברה מוכר (מקס, ישראכרט, כאל, פייבוקס, פפר, הפועלים, לאומי)
- WHOIS: חברה גדולה או פרטיות מוסתרת
- אלפי עובדים, סניפים, מניות בבורסה
- "חברה בע"מ" גדולה, קבוצה עסקית

החזר JSON בלבד:
{"type": "lead_site/small_business/content_site/corporation/bank/insurance/fintech/unknown", "reason": "הסבר קצר", "confidence": 85}"""
    
    try:
        async with AsyncSessionLocal() as session:
            # Update campaign with AI progress
            campaign_result = await session.execute(
                select(ScanCampaign).where(ScanCampaign.id == scan_id)
            )
            campaign = campaign_result.scalar_one_or_none()
            if campaign:
                campaign.ai_total = total_items
                campaign.ai_processed = 0
                campaign.ai_current_domain = "מתחיל..."
                await session.commit()
            
            result = await session.execute(
                select(ScanQueue).where(ScanQueue.id.in_(queue_ids))
            )
            items = result.scalars().all()
            
            for idx, item in enumerate(items):
                try:
                    # Build context from available data
                    context_parts = []
                    context_parts.append(f"🌐 דומיין: {item.domain}")
                    if item.title:
                        context_parts.append(f"📌 כותרת האתר: {item.title}")
                    if item.description:
                        context_parts.append(f"📝 תיאור מגוגל: {item.description}")
                    
                    # ===== נתוני WHOIS =====
                    context_parts.append("\n🔍 נתוני WHOIS:")
                    if item.whois_is_private:
                        context_parts.append("   ⚠️ פרטי WHOIS מוסתרים (סימן לחברה גדולה או שירות פרטיות)")
                    else:
                        if item.owner_name:
                            context_parts.append(f"   👤 בעלים: {item.owner_name}")
                        if item.owner_org:
                            context_parts.append(f"   🏢 ארגון: {item.owner_org}")
                        if item.owner_email:
                            # בדוק אם מייל אישי או מייל עסקי
                            email_type = "אישי" if any(x in item.owner_email.lower() for x in ['gmail', 'yahoo', 'hotmail', 'outlook', 'walla']) else "עסקי"
                            context_parts.append(f"   ✉️ מייל: {item.owner_email} ({email_type})")
                        if item.owner_phone:
                            context_parts.append(f"   📞 טלפון: {item.owner_phone}")
                        if item.registrar:
                            context_parts.append(f"   🏷️ רשם: {item.registrar}")
                        if not any([item.owner_name, item.owner_org, item.owner_email]):
                            context_parts.append("   ❓ אין מידע זמין")
                    
                    # ===== פרטי קשר מהאתר =====
                    if item.emails_found:
                        emails_list = item.emails_found if isinstance(item.emails_found, list) else []
                        if emails_list:
                            context_parts.append(f"\n📧 מיילים מהאתר: {', '.join(emails_list[:5])}")
                    if item.phones_found:
                        phones_list = item.phones_found if isinstance(item.phones_found, list) else []
                        if phones_list:
                            # בדוק אם טלפון נייד
                            mobile_count = sum(1 for p in phones_list if p.startswith('05') or '+9725' in p)
                            context_parts.append(f"   📱 טלפונים: {', '.join(phones_list[:5])} ({mobile_count} ניידים)")
                    
                    # ===== תוכן העמוד =====
                    if item.html_text:
                        page_content = item.html_text[:5000]  # 5000 תווים לניתוח עמוק יותר
                        context_parts.append(f"\n📄 תוכן העמוד (5000 תווים ראשונים):\n{page_content}")
                    
                    user_prompt = "\n".join(context_parts)
                    
                    # Update progress in campaign
                    if campaign:
                        campaign.ai_current_domain = item.domain
                        campaign.ai_processed = idx
                        await session.commit()
                    
                    logger.info(f"🤖 [{idx+1}/{total_items}] Analyzing with GPT: {item.domain} ({len(item.html_text or '')} chars)")
                    
                    response, duration = await gpt.generate(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        temperature=0.3,
                        max_tokens=200
                    )
                    
                    # Parse JSON response (GPT returns clean JSON)
                    import json
                    import re
                    
                    try:
                        parsed = json.loads(response)
                        item.business_type = parsed.get("type", "unknown").lower()
                        item.business_type_reason = parsed.get("reason", "")
                    except:
                        # Fallback: try to extract JSON from response
                        json_match = re.search(r'\{\s*"type"\s*:\s*"([^"]+)".*?"reason"\s*:\s*"([^"]*)"', response, re.DOTALL)
                        if json_match:
                            item.business_type = json_match.group(1).lower()
                            item.business_type_reason = json_match.group(2)
                        else:
                            # Fallback: look for keywords - prioritize corporation indicators
                            response_lower = response.lower()
                            domain_lower = item.domain.lower() if item.domain else ""
                            
                            # Check for credit card companies
                            if any(x in domain_lower for x in ['max', 'isracard', 'cal-online', 'diners', 'visa', 'amex', 'leumi-card']):
                                item.business_type = "corporation"
                            elif any(x in domain_lower for x in ['bank', 'leumi', 'hapoalim', 'discount', 'mizrahi', 'fibi']):
                                item.business_type = "bank"
                            elif any(x in domain_lower for x in ['harel', 'migdal', 'clal', 'phoenix', 'menora', 'ayalon']):
                                item.business_type = "insurance"
                            elif "corporation" in response_lower or "תאגיד" in response or "חברת אשראי" in response:
                                item.business_type = "corporation"
                            elif "bank" in response_lower or "בנק" in response:
                                item.business_type = "bank"
                            elif "insurance" in response_lower or "ביטוח" in response:
                                item.business_type = "insurance"
                            elif "private" in response_lower or "פרטי" in response or "עסק קטן" in response:
                                item.business_type = "private"
                            else:
                                item.business_type = "unknown"
                            
                            item.business_type_reason = response[:200]
                    
                    item.ai_analyzed_at = datetime.utcnow()
                    
                    # Auto-blacklist blocked categories
                    KEEP_CATEGORIES = ["lead_site", "small_business", "private"]
                    if item.business_type and item.business_type not in KEEP_CATEGORIES:
                        item.is_blacklisted = 1
                    else:
                        item.is_blacklisted = 0
                    
                    # Log with emoji based on result
                    emoji = {"private": "🏪", "small_business": "💼", "lead_site": "🎯", 
                             "bank": "🏦", "insurance": "🛡️", "corporation": "🏢",
                             "government": "🏛️", "academia": "🎓", "hospital": "🏥"}.get(item.business_type, "❓")
                    blocked = "🚫" if item.is_blacklisted else "✅"
                    logger.info(f"   {emoji} {blocked} Result: {item.business_type} - {item.business_type_reason[:50] if item.business_type_reason else ''}")
                    
                except Exception as e:
                    logger.error(f"❌ AI analysis failed for {item.domain}: {e}")
                    item.business_type = "error"
                    item.business_type_reason = str(e)
                    item.ai_analyzed_at = datetime.utcnow()
                    item.is_blacklisted = 1  # Error = blocked
            
            # Final update
            if campaign:
                campaign.ai_processed = total_items
                campaign.ai_current_domain = "הושלם ✅"
            
            await session.commit()
            logger.info(f"✅ AI analysis complete for {len(items)} sites")
            
    except Exception as e:
        logger.error(f"AI batch analysis failed: {e}")


@router.get("/{scan_id}/ai-stats")
async def get_ai_stats(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות ניתוח AI
    """
    from sqlalchemy import func
    
    # Count by business type
    result = await session.execute(
        select(ScanQueue.business_type, func.count(ScanQueue.id))
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.business_type != None)
        .group_by(ScanQueue.business_type)
    )
    type_counts = dict(result.all())
    
    # Count not analyzed
    not_analyzed = await session.execute(
        select(func.count(ScanQueue.id))
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.ai_analyzed_at == None)
    )
    
    # Get campaign progress
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    
    return {
        "type_counts": type_counts,
        "not_analyzed": not_analyzed.scalar_one(),
        "private_leads": type_counts.get("private", 0),
        # Real-time progress
        "ai_current_domain": campaign.ai_current_domain if campaign else None,
        "ai_processed": campaign.ai_processed if campaign else 0,
        "ai_total": campaign.ai_total if campaign else 0,
        "is_running": (
            campaign.ai_current_domain not in [None, "", "הושלם ✅", "✅ הושלם!", "נעצר ⏹️"] 
            and not (campaign.ai_current_domain or "").startswith("סורק תוכן")
            and not (campaign.ai_current_domain or "").startswith("סריקת תוכן")
            and not (campaign.ai_current_domain or "").startswith("סורק מחדש")
            and not (campaign.ai_current_domain or "").startswith("בתור")
            and not "הושלם" in (campaign.ai_current_domain or "")
        ) if campaign else False
    }


@router.post("/{scan_id}/stop-ai")
async def stop_ai_analysis(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עצירת ניתוח AI
    """
    global AI_STOP_FLAG
    AI_STOP_FLAG[scan_id] = True
    
    # Update campaign status
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = result.scalar_one_or_none()
    
    if campaign:
        campaign.ai_current_domain = "נעצר ⏹️"
        await session.commit()
    
    logger.info(f"🛑 AI analysis stopped for scan {scan_id}")
    
    return {"message": "ניתוח AI נעצר", "scan_id": scan_id}


@router.post("/stop-all-ai")
async def stop_all_ai_analysis(
    session: AsyncSession = Depends(get_async_session)
):
    """
    עצירת כל ניתוחי ה-AI וניקוי התור
    """
    global AI_STOP_FLAG, AI_QUEUE, AI_CURRENT_SCAN
    
    # Clear the queue
    queue_cleared = len(AI_QUEUE)
    AI_QUEUE = []
    
    # Stop current scan
    if AI_CURRENT_SCAN:
        AI_STOP_FLAG[AI_CURRENT_SCAN] = True
    
    # Get all running scans
    result = await session.execute(select(ScanCampaign))
    campaigns = result.scalars().all()
    
    stopped_count = 0
    for campaign in campaigns:
        if campaign.ai_current_domain and campaign.ai_current_domain not in ["", "הושלם ✅", "נעצר ⏹️"]:
            AI_STOP_FLAG[campaign.id] = True
            campaign.ai_current_domain = "נעצר ⏹️"
            stopped_count += 1
    
    await session.commit()
    
    logger.info(f"🛑 Stopped ALL AI analysis - {stopped_count} scans, cleared {queue_cleared} from queue")
    
    return {
        "message": f"נעצרו {stopped_count} תהליכי AI, נוקו {queue_cleared} מהתור", 
        "stopped": stopped_count,
        "queue_cleared": queue_cleared
    }


@router.post("/{scan_id}/analyze-business-type-selected")
async def analyze_business_type_selected(
    scan_id: int,
    request: dict,
    session: AsyncSession = Depends(get_async_session)
):
    """
    ניתוח סוג העסק באמצעות AI - רק לפריטים שנבחרו
    """
    from loguru import logger
    
    ids = request.get("ids", [])
    
    if not ids:
        return {"message": "לא נבחרו פריטים", "analyzed": 0}
    
    # Verify items belong to this scan
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.id.in_(ids))
    )
    items = result.scalars().all()
    
    if not items:
        return {"message": "לא נמצאו פריטים", "analyzed": 0}
    
    # Start background task
    import asyncio
    asyncio.create_task(run_ai_business_analysis(scan_id, [item.id for item in items]))
    
    return {
        "message": f"מתחיל ניתוח AI של {len(items)} אתרים נבחרים",
        "analyzing": len(items)
    }


# ========== AI Queue Status ==========

@router.get("/ai-queue/status")
async def get_ai_queue_status_route(
    session: AsyncSession = Depends(get_async_session)
):
    """
    מצב תור ה-AI
    """
    global AI_QUEUE, AI_CURRENT_SCAN, AI_QUEUE_RUNNING
    
    queue_info = []
    for idx, scan_id in enumerate(AI_QUEUE):
        result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            queue_info.append({
                "position": idx + 1,
                "scan_id": scan_id,
                "name": campaign.name,
                "ai_total": campaign.ai_total
            })
    
    current_scan_info = None
    if AI_CURRENT_SCAN:
        result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == AI_CURRENT_SCAN)
        )
        campaign = result.scalar_one_or_none()
        if campaign:
            current_scan_info = {
                "scan_id": AI_CURRENT_SCAN,
                "name": campaign.name,
                "ai_current_domain": campaign.ai_current_domain,
                "ai_processed": campaign.ai_processed,
                "ai_total": campaign.ai_total
            }
    
    return {
        "is_running": AI_QUEUE_RUNNING,
        "current_scan": current_scan_info,
        "queue": queue_info,
        "queue_length": len(AI_QUEUE)
    }


# ========== Deep Scan ==========

# Global state for deep scan progress
DEEP_SCAN_STATUS = {}


@router.get("/{scan_id}/deep-scan/status")
async def get_deep_scan_status(scan_id: int):
    """
    קבלת סטטוס סריקה מעמיקה
    """
    return DEEP_SCAN_STATUS.get(scan_id, {
        "is_running": False,
        "current_site": None,
        "processed": 0,
        "total": 0
    })


@router.post("/{scan_id}/deep-scan")
async def start_deep_scan(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    התחלת סריקה מעמיקה לכל האתרים המתאימים בסריקה
    סורק רק אתרים עם business_type = lead_site או small_business
    """
    global DEEP_SCAN_STATUS
    from loguru import logger
    
    # Check if already running
    if DEEP_SCAN_STATUS.get(scan_id, {}).get("is_running"):
        return {"message": "סריקה מעמיקה כבר רצה", "status": DEEP_SCAN_STATUS[scan_id]}
    
    # Get eligible items (lead_site or small_business with content)
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.business_type.in_(["lead_site", "small_business"]))
        .where(ScanQueue.html_text != None)
        .where(ScanQueue.deep_scan_status == "pending")
    )
    items = result.scalars().all()
    
    total = len(items)
    if total == 0:
        return {"message": "אין אתרים מתאימים לסריקה מעמיקה", "total": 0}
    
    # Update ScanCampaign with tracking info
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.deep_scan_status = "running"
        campaign.deep_scan_total = total
        campaign.deep_scan_processed = 0
        campaign.deep_scan_current = None
        await session.commit()
    
    DEEP_SCAN_STATUS[scan_id] = {
        "is_running": True,
        "current_site": None,
        "processed": 0,
        "total": total
    }
    
    logger.info(f"🔍 Starting deep scan for {total} sites in scan {scan_id}")
    
    # Start background task
    import asyncio
    asyncio.create_task(run_deep_scan_for_scan(scan_id, [item.id for item in items]))
    
    return {
        "message": f"מתחיל סריקה מעמיקה של {total} אתרים",
        "total": total
    }


async def run_deep_scan_for_scan(scan_id: int, item_ids: list):
    """
    Background task לסריקה מעמיקה
    """
    global DEEP_SCAN_STATUS
    from app.scraper.deep_scraper import get_deep_scraper
    from app.models.scanned_page import ScannedPage
    from app.database import AsyncSessionLocal
    from loguru import logger
    from datetime import datetime
    
    deep_scraper = get_deep_scraper(max_pages=15)
    
    async with AsyncSessionLocal() as session:
        for item_id in item_ids:
            try:
                # Get item
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                DEEP_SCAN_STATUS[scan_id]["current_site"] = item.domain
                logger.info(f"🔍 Deep scanning: {item.domain}")
                
                # Update status to running
                item.deep_scan_status = "running"
                await session.commit()
                
                # Perform deep scan with timeout
                try:
                    import asyncio
                    scan_result = await asyncio.wait_for(
                        deep_scraper.deep_scan(item.url),
                        timeout=120  # 2 minutes timeout per site
                    )
                except asyncio.TimeoutError:
                    logger.error(f"⏱️ Deep scan timeout for {item.domain}")
                    item.deep_scan_status = "failed"
                    await session.commit()
                    DEEP_SCAN_STATUS[scan_id]["processed"] += 1
                    continue
                except Exception as e:
                    logger.error(f"❌ Deep scan error for {item.domain}: {e}")
                    item.deep_scan_status = "failed"
                    await session.commit()
                    DEEP_SCAN_STATUS[scan_id]["processed"] += 1
                    continue
                
                if scan_result["success"]:
                    # Save scanned pages
                    for page in scan_result["pages"]:
                        scanned_page = ScannedPage(
                            queue_item_id=item_id,
                            url=page["url"],
                            path=page.get("path", "/"),
                            page_type=page.get("page_type", "other"),
                            title=page.get("title", ""),
                            html_text=page.get("html_text", "")[:10000],
                            has_contact_form=page.get("has_contact_form", False),
                            form_html=page.get("form_html", "")[:5000] if page.get("form_html") else None,
                            status="scraped"
                        )
                        session.add(scanned_page)
                    
                    # Update queue item
                    item.deep_scan_status = "completed"
                    item.pages_scanned = scan_result["total_pages"]
                    item.deep_scan_at = datetime.utcnow()
                    
                    await session.commit()
                    logger.info(f"✅ Deep scan complete for {item.domain}: {scan_result['total_pages']} pages")
                else:
                    item.deep_scan_status = "failed"
                    await session.commit()
                    logger.warning(f"❌ Deep scan failed for {item.domain}")
                
                DEEP_SCAN_STATUS[scan_id]["processed"] += 1
                
                # Update campaign progress
                campaign_result = await session.execute(
                    select(ScanCampaign).where(ScanCampaign.id == scan_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    campaign.deep_scan_processed = DEEP_SCAN_STATUS[scan_id]["processed"]
                    campaign.deep_scan_current = item.domain
                    await session.commit()
                
                # Small delay between sites
                import asyncio
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error deep scanning item {item_id}: {e}")
                DEEP_SCAN_STATUS[scan_id]["processed"] += 1
    
    DEEP_SCAN_STATUS[scan_id]["is_running"] = False
    DEEP_SCAN_STATUS[scan_id]["current_site"] = "הושלם ✅"
    logger.info(f"✅ Deep scan completed for scan {scan_id}")
    
    # Final update to campaign
    async with AsyncSessionLocal() as session:
        campaign_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.deep_scan_status = None  # Reset to None instead of "completed"
            campaign.deep_scan_processed = 0
            campaign.deep_scan_total = 0
            campaign.deep_scan_current = None
            await session.commit()


# ========== Calculator Matching ==========

# Global state for matching progress
MATCH_STATUS = {}


@router.get("/{scan_id}/match-calculators/status")
async def get_match_status(scan_id: int):
    """
    קבלת סטטוס התאמת מחשבונים
    """
    return MATCH_STATUS.get(scan_id, {
        "is_running": False,
        "current_site": None,
        "processed": 0,
        "total": 0
    })


@router.post("/{scan_id}/match-calculators")
async def start_match_calculators(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    התאמת מחשבונים לכל האתרים עם תוכן (לא צריך סריקה מעמיקה!)
    משתמש ב-navigation + meta + content מדף הבית
    """
    global MATCH_STATUS
    from loguru import logger
    from app.models.calculator import Calculator
    
    # Check if already running
    if MATCH_STATUS.get(scan_id, {}).get("is_running"):
        return {"message": "התאמה כבר רצה", "status": MATCH_STATUS[scan_id]}
    
    # Get ALL items with content that haven't been matched yet
    from sqlalchemy import or_, func
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.html_text != None)
        .where(func.length(ScanQueue.html_text) > 100)
        .where(ScanQueue.recommended_calc_id == None)
    )
    items = result.scalars().all()
    logger.info(f"🎯 Found {len(items)} items with quality content for matching")
    
    # Get all calculators
    calc_result = await session.execute(select(Calculator).where(Calculator.is_active == True))
    calculators = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "intent_description": c.intent_description,
            "ai_summary": c.ai_summary,
            "keywords": c.keywords
        }
        for c in calc_result.scalars().all()
    ]
    
    total = len(items)
    if total == 0:
        return {"message": "אין אתרים להתאמה", "total": 0}
    
    # Update ScanCampaign with tracking info
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.calc_match_status = "running"
        campaign.calc_match_total = total
        campaign.calc_match_processed = 0
        await session.commit()
    
    MATCH_STATUS[scan_id] = {
        "is_running": True,
        "current_site": None,
        "processed": 0,
        "total": total
    }
    
    logger.info(f"🧮 Starting calculator matching for {total} sites in scan {scan_id}")
    
    # Start background task
    import asyncio
    asyncio.create_task(run_match_calculators(scan_id, [item.id for item in items], calculators))
    
    return {
        "message": f"מתחיל התאמת מחשבונים ל-{total} אתרים",
        "total": total,
        "calculators_count": len(calculators)
    }


async def run_match_calculators(scan_id: int, item_ids: list, calculators: list):
    """
    Background task להתאמת מחשבונים
    """
    global MATCH_STATUS
    from app.ai.calculator_matcher import get_calculator_matcher
    from app.scraper.deep_scraper import DeepScraper
    from app.models.scanned_page import ScannedPage
    from app.database import AsyncSessionLocal
    from loguru import logger
    from datetime import datetime
    
    matcher = get_calculator_matcher()
    
    async with AsyncSessionLocal() as session:
        for item_id in item_ids:
            try:
                # Get item with scanned pages
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                MATCH_STATUS[scan_id]["current_site"] = item.domain
                logger.info(f"🧮 Matching calculator for: {item.domain}")
                
                # Build content summary from navigation + meta + content (no deep scan needed!)
                content_parts = []
                
                # Add navigation menu items
                if item.nav_links:
                    try:
                        import json
                        nav_data = json.loads(item.nav_links)
                        nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
                        if nav_texts:
                            content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
                    except:
                        pass
                
                # Add meta information
                if item.meta_title:
                    content_parts.append(f"=== כותרת ===\n{item.meta_title}")
                if item.meta_description:
                    content_parts.append(f"=== תיאור ===\n{item.meta_description}")
                if item.meta_keywords:
                    content_parts.append(f"=== מילות מפתח ===\n{item.meta_keywords}")
                
                # Add page content
                if item.html_text:
                    content_parts.append(f"=== תוכן העמוד ===\n{item.html_text[:3000]}")
                
                # Special flag if calculator in menu
                if item.has_menu_calculator:
                    content_parts.append("=== מידע נוסף ===\nיש קישור למחשבון בתפריט הראשי")
                
                site_content = "\n\n".join(content_parts)[:6000]
                
                # Match calculator
                match_result = await matcher.match_calculator(
                    site_content=site_content,
                    business_type=item.business_type or "unknown",
                    calculators=calculators
                )
                
                if match_result["success"]:
                    item.recommended_calc_id = match_result["calc_id"]
                    item.recommended_calc_score = match_result["match_score"]
                    item.recommended_calc_reason = match_result["reasoning"]
                    item.suggested_new_calc = match_result.get("suggested_new_calc")
                    # שמור את כל ההתאמות כ-JSON
                    if match_result.get("all_matches"):
                        import json
                        item.all_recommended_calcs = json.dumps(match_result["all_matches"], ensure_ascii=False)
                    item.calc_matched_at = datetime.utcnow()
                    await session.commit()
                    
                    if match_result["calc_id"]:
                        logger.info(f"✅ Matched {item.domain} with calc {match_result['calc_id']} (score: {match_result['match_score']:.2f})")
                    elif match_result.get("suggested_new_calc"):
                        logger.info(f"💡 No match for {item.domain}, suggested new calc: {match_result['suggested_new_calc'][:50]}...")
                    else:
                        logger.warning(f"❌ Failed to match {item.domain}")
                else:
                    logger.warning(f"❌ Error matching {item.domain}: {match_result.get('reasoning')}")
                
                MATCH_STATUS[scan_id]["processed"] += 1
                
                # Update campaign progress
                campaign_result = await session.execute(
                    select(ScanCampaign).where(ScanCampaign.id == scan_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    campaign.calc_match_processed = MATCH_STATUS[scan_id]["processed"]
                    await session.commit()
                
                # Delay between API calls
                import asyncio
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error matching calculator for item {item_id}: {e}")
                MATCH_STATUS[scan_id]["processed"] += 1
    
    MATCH_STATUS[scan_id]["is_running"] = False
    MATCH_STATUS[scan_id]["current_site"] = "הושלם ✅"
    logger.info(f"✅ Calculator matching completed for scan {scan_id}")
    
    # Final update to campaign
    async with AsyncSessionLocal() as session:
        campaign_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.calc_match_status = None  # Reset to None instead of "completed"
            campaign.calc_match_processed = 0
            campaign.calc_match_total = 0
            campaign.calc_match_current = None
            await session.commit()


# ========== GPT Calculator Matching ==========

# Global state for GPT matching progress
GPT_MATCH_STATUS = {}


@router.get("/{scan_id}/match-calculators-gpt/status")
async def get_gpt_match_status(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת סטטוס התאמת מחשבונים GPT
    """
    # First check in-memory status (for live updates)
    if scan_id in GPT_MATCH_STATUS:
        return GPT_MATCH_STATUS[scan_id]
    
    # Otherwise, check database for campaign status
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    
    if campaign and campaign.gpt_match_status == "running":
        return {
            "is_running": True,
            "current_site": "Loading...",
            "processed": campaign.gpt_match_processed or 0,
            "total": campaign.gpt_match_total or 0,
            "logs": []
        }
    
    return {
        "is_running": False,
        "current_site": None,
        "processed": 0,
        "total": 0,
        "logs": []
    }


@router.post("/{scan_id}/match-calculators-gpt")
async def start_match_calculators_gpt(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    התאמת מחשבונים לכל האתרים עם תוכן באמצעות OpenAI GPT
    שומר תוצאות בשדות GPT נפרדים להשוואה
    """
    global GPT_MATCH_STATUS
    from loguru import logger
    from app.models.calculator import Calculator
    
    # Check if already running
    if GPT_MATCH_STATUS.get(scan_id, {}).get("is_running"):
        return {"message": "התאמת GPT כבר רצה", "status": GPT_MATCH_STATUS[scan_id]}
    
    # Get ALL items with content that haven't been GPT-matched yet
    from sqlalchemy import or_, func
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.html_text != None)
        .where(func.length(ScanQueue.html_text) > 100)
        .where(ScanQueue.gpt_recommended_calc_id == None)
    )
    items = result.scalars().all()
    logger.info(f"⚡ Found {len(items)} items for GPT matching")
    
    # Get all calculators
    calc_result = await session.execute(select(Calculator).where(Calculator.is_active == True))
    calculators = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "intent_description": c.intent_description,
            "ai_summary": c.ai_summary,
            "keywords": c.keywords
        }
        for c in calc_result.scalars().all()
    ]
    
    total = len(items)
    if total == 0:
        return {"message": "אין אתרים להתאמת GPT", "total": 0}
    
    # Update ScanCampaign with GPT tracking info
    campaign_result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    campaign = campaign_result.scalar_one_or_none()
    if campaign:
        campaign.gpt_match_status = "running"
        campaign.gpt_match_total = total
        campaign.gpt_match_processed = 0
        await session.commit()
    
    GPT_MATCH_STATUS[scan_id] = {
        "is_running": True,
        "current_site": None,
        "processed": 0,
        "total": total,
        "logs": []
    }
    
    logger.info(f"⚡ Starting GPT calculator matching for {total} sites in scan {scan_id}")
    
    # Start background task
    import asyncio
    asyncio.create_task(run_match_calculators_gpt(scan_id, [item.id for item in items], calculators))
    
    return {
        "message": f"מתחיל התאמת GPT ל-{total} אתרים",
        "total": total,
        "calculators_count": len(calculators)
    }


async def run_match_calculators_gpt(scan_id: int, item_ids: list, calculators: list):
    """
    Background task להתאמת מחשבונים עם GPT
    """
    global GPT_MATCH_STATUS
    from app.ai.calculator_matcher import get_calculator_matcher
    from app.database import AsyncSessionLocal
    from loguru import logger
    from datetime import datetime
    
    matcher = get_calculator_matcher()
    
    async with AsyncSessionLocal() as session:
        for item_id in item_ids:
            try:
                # Get item
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                GPT_MATCH_STATUS[scan_id]["current_site"] = item.domain
                logger.info(f"⚡ GPT Matching calculator for: {item.domain}")
                
                # Build content summary from navigation + meta + content
                content_parts = []
                
                if item.nav_links:
                    try:
                        import json
                        nav_data = json.loads(item.nav_links)
                        nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
                        if nav_texts:
                            content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
                    except:
                        pass
                
                if item.meta_title:
                    content_parts.append(f"=== כותרת ===\n{item.meta_title}")
                if item.meta_description:
                    content_parts.append(f"=== תיאור ===\n{item.meta_description}")
                if item.meta_keywords:
                    content_parts.append(f"=== מילות מפתח ===\n{item.meta_keywords}")
                
                if item.html_text:
                    content_parts.append(f"=== תוכן העמוד ===\n{item.html_text[:3000]}")
                
                if item.has_menu_calculator:
                    content_parts.append("=== מידע נוסף ===\nיש קישור למחשבון בתפריט הראשי")
                
                site_content = "\n\n".join(content_parts)[:6000]
                
                # Match with GPT!
                match_result = await matcher.match_calculator_gpt(
                    site_content=site_content,
                    business_type=item.business_type or "unknown",
                    calculators=calculators
                )
                
                if match_result["success"]:
                    item.gpt_recommended_calc_id = match_result["calc_id"]
                    item.gpt_recommended_calc_score = match_result["match_score"]
                    item.gpt_recommended_calc_reason = match_result["reasoning"]
                    item.gpt_suggested_new_calc = match_result.get("suggested_new_calc")
                    item.gpt_match_duration_seconds = match_result.get("duration_seconds", 0)
                    
                    if match_result.get("all_matches"):
                        import json
                        item.gpt_all_recommended_calcs = json.dumps(match_result["all_matches"], ensure_ascii=False)
                    item.gpt_matched_at = datetime.utcnow()
                    await session.commit()
                    
                    # 🚀 Auto-create lead if eligible
                    await auto_create_lead_from_scan(session, item)
                    
                    duration = match_result.get("duration_seconds", 0)
                    log_entry = f"✅ {item.domain} - {duration:.1f}s - calc {match_result['calc_id']}"
                    GPT_MATCH_STATUS[scan_id]["logs"].append(log_entry)
                    # Keep only last 20 logs
                    GPT_MATCH_STATUS[scan_id]["logs"] = GPT_MATCH_STATUS[scan_id]["logs"][-20:]
                    
                    logger.info(f"⚡ GPT Matched {item.domain} with calc {match_result['calc_id']} in {duration:.2f}s")
                else:
                    logger.warning(f"❌ GPT Error matching {item.domain}: {match_result.get('reasoning')}")
                    GPT_MATCH_STATUS[scan_id]["logs"].append(f"❌ {item.domain} - error")
                
                GPT_MATCH_STATUS[scan_id]["processed"] += 1
                
                # Update campaign progress
                campaign_result = await session.execute(
                    select(ScanCampaign).where(ScanCampaign.id == scan_id)
                )
                campaign = campaign_result.scalar_one_or_none()
                if campaign:
                    campaign.gpt_match_processed = GPT_MATCH_STATUS[scan_id]["processed"]
                    await session.commit()
                
                # Short delay between API calls
                import asyncio
                await asyncio.sleep(1)  # GPT is faster, shorter delay
                
            except Exception as e:
                logger.error(f"Error in GPT matching for item {item_id}: {e}")
                GPT_MATCH_STATUS[scan_id]["logs"].append(f"❌ Error: {str(e)[:50]}")
                GPT_MATCH_STATUS[scan_id]["processed"] += 1
    
    GPT_MATCH_STATUS[scan_id]["is_running"] = False
    GPT_MATCH_STATUS[scan_id]["current_site"] = "הושלם ✅"
    logger.info(f"⚡ GPT Calculator matching completed for scan {scan_id}")
    
    # Final update to campaign
    async with AsyncSessionLocal() as session:
        campaign_result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == scan_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            campaign.gpt_match_status = "completed"
            await session.commit()


# ========== Global Rescan & Match ==========

# Global status for rescan and match operation
GLOBAL_RESCAN_STATUS = {
    "is_running": False,
    "phase": None,  # "rescan" or "match"
    "current_site": None,
    "rescan_processed": 0,
    "rescan_total": 0,
    "match_processed": 0,
    "match_total": 0,
    "logs": []
}


@router.get("/global/rescan-matched-no-content/status")
async def get_global_rescan_status():
    """
    קבלת סטטוס סריקה גלובלית
    """
    return GLOBAL_RESCAN_STATUS


@router.post("/global/rescan-matched-no-content/stop")
async def stop_global_rescan():
    """
    עצירת סריקה גלובלית
    """
    global GLOBAL_RESCAN_STATUS
    GLOBAL_RESCAN_STATUS["is_running"] = False
    GLOBAL_RESCAN_STATUS["logs"].append("🛑 נעצר ידנית")
    return {"message": "נעצר", "status": GLOBAL_RESCAN_STATUS}


@router.post("/global/rescan-matched-no-content")
async def global_rescan_matched_without_content(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקה גלובלית: מביא תוכן לכל הדומיינים המותאמים ללא תוכן,
    ואז מריץ התאמת מחשבונים GPT עליהם.
    """
    global GLOBAL_RESCAN_STATUS
    from loguru import logger
    from sqlalchemy import or_, func
    from app.models.calculator import Calculator
    
    # Check if already running
    if GLOBAL_RESCAN_STATUS.get("is_running"):
        return {"message": "סריקה גלובלית כבר רצה", "status": GLOBAL_RESCAN_STATUS}
    
    # Get all matched items without content (not blacklisted)
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.status == "matched")
        .where(or_(
            ScanQueue.html_text == None,
            func.length(ScanQueue.html_text) < 100
        ))
        .where(or_(
            ScanQueue.is_blacklisted == None,
            ScanQueue.is_blacklisted == 0
        ))
    )
    items = result.scalars().all()
    
    total = len(items)
    if total == 0:
        return {"message": "כל הדומיינים המותאמים כבר נסרקו", "rescan_count": 0}
    
    # Get all calculators for matching phase
    calc_result = await session.execute(select(Calculator).where(Calculator.is_active == True))
    calculators = [
        {
            "id": c.id,
            "name": c.name,
            "category": c.category,
            "intent_description": c.intent_description,
            "ai_summary": c.ai_summary,
            "keywords": c.keywords
        }
        for c in calc_result.scalars().all()
    ]
    
    # Initialize status
    GLOBAL_RESCAN_STATUS = {
        "is_running": True,
        "phase": "rescan",
        "current_site": None,
        "rescan_processed": 0,
        "rescan_total": total,
        "match_processed": 0,
        "match_total": 0,
        "logs": [f"🚀 מתחיל סריקת {total} דומיינים ללא תוכן"]
    }
    
    logger.info(f"🌐 Starting global rescan for {total} matched domains without content")
    
    # Start background task
    import asyncio
    asyncio.create_task(run_global_rescan_and_match([item.id for item in items], calculators))
    
    return {
        "message": f"מתחיל סריקה גלובלית של {total} דומיינים",
        "rescan_count": total,
        "calculators_count": len(calculators)
    }


async def run_global_rescan_and_match(item_ids: list, calculators: list):
    """
    Background task - סריקת תוכן + התאמת מחשבון GPT
    """
    global GLOBAL_RESCAN_STATUS
    from app.scraper.smart_scraper import get_smart_scraper
    from app.ai.calculator_matcher import get_calculator_matcher
    from app.database import AsyncSessionLocal
    from loguru import logger
    from datetime import datetime
    import asyncio
    
    scraper = get_smart_scraper()
    matcher = get_calculator_matcher()
    
    # Phase 1: Rescan for content
    GLOBAL_RESCAN_STATUS["phase"] = "rescan"
    items_with_new_content = []
    
    async with AsyncSessionLocal() as session:
        total = len(item_ids)
        
        for idx, item_id in enumerate(item_ids):
            if not GLOBAL_RESCAN_STATUS["is_running"]:
                logger.info("🛑 Global rescan stopped by user")
                break
            
            try:
                # Get item
                result = await session.execute(
                    select(ScanQueue).where(ScanQueue.id == item_id)
                )
                item = result.scalar_one_or_none()
                if not item:
                    continue
                
                GLOBAL_RESCAN_STATUS["current_site"] = item.domain
                logger.info(f"🔄 [{idx+1}/{total}] Rescanning: {item.domain}")
                
                # Scrape content - try ZenRows directly for better results
                scrape_result = await scraper.scrape_with_zenrows_first(item.url)
                
                if scrape_result and not scrape_result.get("error"):
                    new_content = scrape_result.get("inner_text", "")
                    
                    if len(new_content) >= 100:
                        item.html_body = scrape_result.get("html", "")[:50000]
                        item.html_text = new_content[:15000]
                        item.title = scrape_result.get("title", item.title)
                        
                        # Store navigation and meta data
                        if scrape_result.get("nav_links"):
                            import json
                            item.nav_links = json.dumps(scrape_result["nav_links"], ensure_ascii=False)
                        if scrape_result.get("meta_description"):
                            item.meta_description = scrape_result["meta_description"][:1000]
                        if scrape_result.get("meta_keywords"):
                            item.meta_keywords = scrape_result["meta_keywords"][:500]
                        if scrape_result.get("has_menu_calculator") is not None:
                            item.has_menu_calculator = 1 if scrape_result["has_menu_calculator"] else 0
                        
                        await session.commit()
                        items_with_new_content.append(item_id)
                        
                        log_entry = f"✅ {item.domain} - {len(new_content)} chars"
                        GLOBAL_RESCAN_STATUS["logs"].append(log_entry)
                        logger.info(f"✅ Got content for {item.domain}: {len(new_content)} chars")
                    else:
                        log_entry = f"⚠️ {item.domain} - תוכן קצר מדי"
                        GLOBAL_RESCAN_STATUS["logs"].append(log_entry)
                else:
                    error = scrape_result.get("error", "Unknown") if scrape_result else "Failed"
                    log_entry = f"❌ {item.domain} - {error[:30]}"
                    GLOBAL_RESCAN_STATUS["logs"].append(log_entry)
                
                # Keep only last 30 logs
                GLOBAL_RESCAN_STATUS["logs"] = GLOBAL_RESCAN_STATUS["logs"][-30:]
                GLOBAL_RESCAN_STATUS["rescan_processed"] = idx + 1
                
                # Small delay between requests
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error rescanning {item_id}: {e}")
                GLOBAL_RESCAN_STATUS["logs"].append(f"❌ Error: {str(e)[:30]}")
                GLOBAL_RESCAN_STATUS["rescan_processed"] = idx + 1
    
    # Phase 2: Match calculators for items that got content
    if GLOBAL_RESCAN_STATUS["is_running"] and items_with_new_content:
        GLOBAL_RESCAN_STATUS["phase"] = "match"
        GLOBAL_RESCAN_STATUS["match_total"] = len(items_with_new_content)
        GLOBAL_RESCAN_STATUS["logs"].append(f"🎯 עובר לשלב התאמת מחשבונים ({len(items_with_new_content)} דומיינים)")
        
        async with AsyncSessionLocal() as session:
            for idx, item_id in enumerate(items_with_new_content):
                if not GLOBAL_RESCAN_STATUS["is_running"]:
                    break
                
                try:
                    # Get item
                    result = await session.execute(
                        select(ScanQueue).where(ScanQueue.id == item_id)
                    )
                    item = result.scalar_one_or_none()
                    if not item:
                        continue
                    
                    GLOBAL_RESCAN_STATUS["current_site"] = f"התאמה: {item.domain}"
                    logger.info(f"⚡ [{idx+1}/{len(items_with_new_content)}] GPT Matching: {item.domain}")
                    
                    # Build content summary
                    content_parts = []
                    
                    if item.nav_links:
                        try:
                            import json
                            nav_data = json.loads(item.nav_links)
                            nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
                            if nav_texts:
                                content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
                        except:
                            pass
                    
                    if item.meta_description:
                        content_parts.append(f"=== תיאור ===\n{item.meta_description}")
                    if item.meta_keywords:
                        content_parts.append(f"=== מילות מפתח ===\n{item.meta_keywords}")
                    
                    if item.html_text:
                        content_parts.append(f"=== תוכן העמוד ===\n{item.html_text[:3000]}")
                    
                    site_content = "\n\n".join(content_parts)[:6000]
                    
                    # Match with GPT
                    match_result = await matcher.match_calculator_gpt(
                        site_content=site_content,
                        business_type=item.business_type or "unknown",
                        calculators=calculators
                    )
                    
                    if match_result["success"]:
                        item.gpt_recommended_calc_id = match_result["calc_id"]
                        item.gpt_recommended_calc_score = match_result["match_score"]
                        item.gpt_recommended_calc_reason = match_result["reasoning"]
                        item.gpt_suggested_new_calc = match_result.get("suggested_new_calc")
                        item.gpt_match_duration_seconds = match_result.get("duration_seconds", 0)
                        
                        if match_result.get("all_matches"):
                            import json
                            item.gpt_all_recommended_calcs = json.dumps(match_result["all_matches"], ensure_ascii=False)
                        item.gpt_matched_at = datetime.utcnow()
                        await session.commit()
                        
                        # 🚀 Auto-create lead if eligible
                        await auto_create_lead_from_scan(session, item)
                        
                        log_entry = f"🎯 {item.domain} → מחשבון {match_result['calc_id']}"
                        GLOBAL_RESCAN_STATUS["logs"].append(log_entry)
                        logger.info(f"⚡ Matched {item.domain} with calc {match_result['calc_id']}")
                    else:
                        GLOBAL_RESCAN_STATUS["logs"].append(f"❌ {item.domain} - לא נמצאה התאמה")
                    
                    # Keep only last 30 logs
                    GLOBAL_RESCAN_STATUS["logs"] = GLOBAL_RESCAN_STATUS["logs"][-30:]
                    GLOBAL_RESCAN_STATUS["match_processed"] = idx + 1
                    
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error matching {item_id}: {e}")
                    GLOBAL_RESCAN_STATUS["logs"].append(f"❌ Match error: {str(e)[:30]}")
                    GLOBAL_RESCAN_STATUS["match_processed"] = idx + 1
    
    # Complete
    GLOBAL_RESCAN_STATUS["is_running"] = False
    GLOBAL_RESCAN_STATUS["phase"] = "completed"
    GLOBAL_RESCAN_STATUS["current_site"] = "הושלם ✅"
    GLOBAL_RESCAN_STATUS["logs"].append(f"🎉 הושלם! נסרקו {GLOBAL_RESCAN_STATUS['rescan_processed']}, הותאמו {GLOBAL_RESCAN_STATUS['match_processed']}")
    logger.info(f"🌐 Global rescan completed: {GLOBAL_RESCAN_STATUS['rescan_processed']} rescanned, {GLOBAL_RESCAN_STATUS['match_processed']} matched")


# ========== Convert to Leads ==========

@router.post("/{scan_id}/convert-to-leads")
async def convert_matched_to_leads(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    המרת כל האתרים המותאמים ללידים
    """
    from app.models.lead import Lead
    from loguru import logger
    from datetime import datetime
    
    # Get matched items
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.recommended_calc_id != None)
    )
    items = result.scalars().all()
    
    if not items:
        return {"message": "אין אתרים מותאמים להמרה", "converted": 0}
    
    converted = 0
    skipped = 0
    
    for item in items:
        # Check if lead already exists for this domain
        existing = await session.execute(
            select(Lead).where(Lead.domain == item.domain)
        )
        if existing.scalar_one_or_none():
            skipped += 1
            continue
        
        # Create new lead
        contact_info = {}
        if item.owner_email:
            contact_info["whois_email"] = item.owner_email
        if item.owner_name:
            contact_info["whois_name"] = item.owner_name
        if item.owner_phone:
            contact_info["whois_phone"] = item.owner_phone
        if item.owner_org:
            contact_info["whois_org"] = item.owner_org
        
        lead = Lead(
            domain=item.domain,
            site_name=item.title or item.domain,
            category=item.business_type,
            recommended_calc_id=item.recommended_calc_id,
            source_campaign_id=scan_id,
            status="matched",
            contact_info=contact_info,
            ai_status={
                "calc_score": item.recommended_calc_score,
                "calc_reason": item.recommended_calc_reason
            }
        )
        
        session.add(lead)
        converted += 1
    
    await session.commit()
    logger.info(f"✅ Converted {converted} items to leads, skipped {skipped} existing")
    
    return {
        "message": f"הומרו {converted} אתרים ללידים",
        "converted": converted,
        "skipped": skipped
    }


# ========== GPU Control ==========

@router.get("/gpu/status")
async def get_gpu_status():
    """
    קבלת סטטוס GPU ומודלים טעונים
    """
    from app.ai.ollama_client import get_ollama_client
    
    ollama = get_ollama_client()
    return await ollama.get_gpu_status()


@router.post("/gpu/load")
async def load_model_to_gpu():
    """
    טעינת המודל ל-GPU (שומר חם 24 שעות)
    """
    from app.ai.ollama_client import get_ollama_client
    
    ollama = get_ollama_client()
    return await ollama.load_model()


@router.post("/gpu/unload")
async def unload_model_from_gpu():
    """
    הורדת המודל מה-GPU (משחרר זיכרון)
    [DEPRECATED - Ollama removed, kept for backward compatibility]
    """
    from app.ai.ollama_client import get_ollama_client
    
    ollama = get_ollama_client()
    return await ollama.unload_model()


# ========== NEW PIPELINE ENDPOINTS (v2) ==========

@router.post("/{scan_id}/pipeline/start")
async def start_pipeline(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    🚀 Start full pipeline for a scan
    
    This is the new simplified flow:
    Apify (already done) -> ZenRows -> GPT Classification -> WHOIS -> Lead
    
    Runs in background with 5 concurrent URLs.
    Use /pipeline/status to check progress.
    """
    import asyncio
    from app.services.pipeline_service import PipelineService, PIPELINE_ACTIVE
    
    # Check if already running
    if PIPELINE_ACTIVE.get(scan_id, False):
        return {"status": "already_running", "message": "Pipeline already running"}
    
    # Verify scan exists
    result = await session.execute(
        select(ScanCampaign).where(ScanCampaign.id == scan_id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    # Start pipeline in background
    service = PipelineService()
    asyncio.create_task(service.run_pipeline(scan_id))
    
    return {
        "status": "started",
        "message": f"Pipeline started for scan {scan_id}",
        "scan_name": scan.name
    }


@router.post("/{scan_id}/pipeline/stop")
async def stop_pipeline(scan_id: int):
    """
    ⏹️ Stop running pipeline
    """
    from app.services.pipeline_service import PipelineService
    
    await PipelineService.stop_pipeline(scan_id)
    return {"status": "stopping", "message": "Stop signal sent"}


@router.post("/{scan_id}/pipeline/retry-failed")
async def retry_failed_items(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    🔄 Reset failed items to pending so they can be retried
    """
    from app.models.scan_campaign import PipelineStage
    
    # Reset failed items
    result = await session.execute(
        select(ScanQueue)
        .where(ScanQueue.campaign_id == scan_id)
        .where(ScanQueue.pipeline_stage == PipelineStage.FAILED)
    )
    failed_items = result.scalars().all()
    
    count = 0
    for item in failed_items:
        item.pipeline_stage = PipelineStage.PENDING
        item.retry_count = 0
        item.error_message = None
        count += 1
    
    await session.commit()
    
    logger.info(f"🔄 Reset {count} failed items to pending for scan {scan_id}")
    
    return {
        "status": "reset",
        "message": f"אופסו {count} דומיינים שנכשלו",
        "reset_count": count
    }


@router.get("/{scan_id}/pipeline/status")
async def get_pipeline_status(
    scan_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    📊 Get pipeline status with progress stats
    
    Returns counts for each pipeline stage.
    """
    from app.models.scan_campaign import PipelineStage, PIPELINE_STAGE_LABELS
    from app.services.pipeline_service import PIPELINE_ACTIVE
    
    # Get counts by stage
    result = await session.execute(
        select(
            ScanQueue.pipeline_stage,
            func.count(ScanQueue.id).label('count')
        )
        .where(ScanQueue.campaign_id == scan_id)
        .group_by(ScanQueue.pipeline_stage)
    )
    stage_counts = {row.pipeline_stage or 0: row.count for row in result.fetchall()}
    
    # Get total
    total_result = await session.execute(
        select(func.count(ScanQueue.id))
        .where(ScanQueue.campaign_id == scan_id)
    )
    total = total_result.scalar() or 0
    
    # Build response
    stages = {
        "pending": stage_counts.get(PipelineStage.PENDING, 0),
        "scraped": stage_counts.get(PipelineStage.SCRAPED, 0),
        "classified": stage_counts.get(PipelineStage.CLASSIFIED, 0),
        "whois_done": stage_counts.get(PipelineStage.WHOIS_DONE, 0),
        "lead_created": stage_counts.get(PipelineStage.LEAD_CREATED, 0),
        "filtered": stage_counts.get(PipelineStage.FILTERED, 0),
        "failed": stage_counts.get(PipelineStage.FAILED, 0),
    }
    
    completed = stages["lead_created"] + stages["filtered"] + stages["failed"]
    
    return {
        "is_running": PIPELINE_ACTIVE.get(scan_id, False),
        "total": total,
        "completed": completed,
        "progress_percent": round((completed / total * 100) if total > 0 else 0, 1),
        "stages": stages,
        "leads_created": stages["lead_created"],
        "filtered_out": stages["filtered"],
        "failed": stages["failed"]
    }


@router.get("/{scan_id}/queue/v2")
async def get_scan_queue_v2(
    scan_id: int,
    limit: int = Query(100, description="Max items"),
    offset: int = Query(0, description="Offset"),
    stage: Optional[int] = Query(None, description="Filter by pipeline stage"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    📋 Get scan queue with pipeline stage info (v2)
    
    Returns items with proper pipeline_stage and all fields for display.
    """
    from app.models.scan_campaign import PipelineStage, PIPELINE_STAGE_LABELS
    
    query = select(ScanQueue).where(ScanQueue.campaign_id == scan_id)
    
    if stage is not None:
        query = query.where(ScanQueue.pipeline_stage == stage)
    
    query = query.order_by(ScanQueue.pipeline_stage.desc(), ScanQueue.id.desc())
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return [
        {
            "id": item.id,
            "domain": item.domain,
            "url": item.url,
            "title": item.title or item.meta_title,
            
            # Pipeline info
            "pipeline_stage": item.pipeline_stage or 0,
            "pipeline_stage_label": PIPELINE_STAGE_LABELS.get(
                PipelineStage(item.pipeline_stage or 0), "ממתין"
            ),
            "retry_count": item.retry_count or 0,
            
            # Business type
            "business_type": item.business_type,
            "business_type_reason": item.business_type_reason,
            
            # WHOIS
            "whois_name": item.owner_name,
            "whois_org": item.owner_org,
            "whois_email": item.owner_email,
            "whois_phone": item.owner_phone,
            "whois_private": bool(item.whois_is_private),
            
            # Contact info from page
            "emails": item.emails_found or [],
            "phones": item.phones_found or [],
            
            # Content
            "has_content": bool(item.html_text),
            "content_preview": (item.html_text or "")[:200],
            
            # Status
            "is_blacklisted": bool(item.is_blacklisted),
            "error_message": item.error_message,
            
            # Timestamps
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "stage_updated_at": item.stage_updated_at.isoformat() if item.stage_updated_at else None,
        }
        for item in items
    ]
