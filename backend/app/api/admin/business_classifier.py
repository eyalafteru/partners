"""
PartnerCalc OS - Global Business Classifier
סיווג גלובלי של כל הדומיינים במערכת באמצעות GPT
מסנן: בנקים, ביטוח, ממשלה, אקדמיה, בתי חולים, חדשות, תאגידים
משאיר: עסקים קטנים ואתרי לידים
"""
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
import json
import asyncio

from app.database import get_async_session, AsyncSessionLocal
from app.models.scan_campaign import ScanQueue
from app.models.lead import Lead
from app.ai.openai_client import get_openai_client

router = APIRouter()

# ========== Global State ==========

CLASSIFY_STATUS = {
    "running": False,
    "stopped": False,
    "phase": "",
    "total": 0,
    "processed": 0,
    "pre_filtered": 0,
    "gpt_classified": 0,
    "kept": 0,
    "blocked": 0,
    "current_domain": "",
    "started_at": None,
    "results_by_type": {}
}

# ========== Blocked Domain Patterns ==========

BLOCKED_PATTERNS = {
    # Government
    "government": [
        ".gov.il", "mof.gov", "health.gov", "edu.gov", "justice.gov",
        "police.gov", "mod.gov", "mfa.gov", "municipality", "iriya",
        "btl.gov", "taxes.gov", "water.gov", "energy.gov", "moag.gov",
        "economy.gov", "pmo.gov", "knesset.gov", "court.gov"
    ],
    
    # Academia
    "academia": [
        ".ac.il", "university", "college", "technion", "weizmann",
        "tau.ac", "huji.ac", "bgu.ac", "openu.ac", "ariel.ac",
        "haifa.ac", "biu.ac", "idc.ac", "jce.ac", "ruppin.ac",
        "sapir.ac", "yvc.ac", "hit.ac", "sce.ac", "afeka.ac",
        "shenkar.ac", "bezalel.ac"
    ],
    
    # Banks
    "bank": [
        "leumi", "hapoalim", "discount", "mizrahi", "fibi",
        "bankisrael", "boi.org", "bank-of", "unionbank", "otsar",
        "yahav", "mercantile", "massad"
    ],
    
    # Insurance
    "insurance": [
        "harel", "migdal", "clal-ins", "phoenix", "menora",
        "ayalon", "shlomo-ins", "the-phoenix", "dikla", "psagot",
        "altshuler", "meitav", "more-invest", "fnx.co.il", "phenix"
    ],
    
    # Credit cards / Large Corporations / Car Rental
    "corporation": [
        "max.co.il", "isracard", "cal-online", "visa", "amex",
        "diners", "leumi-card", "bezeq", "cellcom", "partner",
        "hot.net", "pelephone", "012", "013", "elco", "strauss",
        "osem", "tnuva", "shikun", "azrieli", "amdocs", "teva",
        "israel-electric", "mekorot", "bezek",
        "shlomo.co.il", "sixt", "gamaf.co.il", "eldan", "avis", "hertz", "budget"
    ],
    
    # Healthcare
    "hospital": [
        "sheba", "ichilov", "hadassah", "rambam", "clalit",
        "maccabi", "meuhedet", "leumit", "hospital", "soroka",
        "wolfson", "assuta", "beilinson", "kaplan", "carmel",
        "emek", "poriya", "ziv", "galilee-med"
    ],
    
    # News / Media
    "news": [
        "ynet", "walla", "mako", "globes", "calcalist", "themarker",
        "news.co.il", "israelhayom", "maariv", "haaretz", "n12.co.il",
        "kan.org", "reshet", "keshet", "channel", "news1", "ice.co.il",
        "sport5", "one.co.il"
    ],
    
    # Large e-commerce / Classifieds
    "ecommerce_giant": [
        "amazon", "aliexpress", "ebay", "shufersal", "rami-levy",
        "victory", "tiv-taam", "mega.co.il", "zap.co.il", "ivory",
        "ksp.co.il", "bug.co.il", "wisebuy", "next.co.il",
        "yad2.co.il", "yad1", "winwin", "homeless.co.il", "drushim"
    ],
    
    # Fintech (large)
    "fintech": [
        "pepper", "one-zero", "onezero", "bit.co.il", "paybox",
        "paypal", "tranzila", "cardcom", "creditguard", "blender.co.il",
        "5555.co.il", "555.co.il"
    ],
    
    # Religious
    "religious": [
        "yeshiva", "kollel", "dati", "chabad", "mafdal",
        "moetzet", "rabbanut", "kashrut", "synagogue", "beit-knesset"
    ]
}

# Categories to KEEP
KEEP_CATEGORIES = ["lead_site", "small_business"]

# Categories to BLOCK
BLOCK_CATEGORIES = [
    "bank", "insurance", "corporation", "fintech", "government",
    "academia", "hospital", "nonprofit", "news", "ecommerce_giant", "religious"
]


# ========== Helper Functions ==========

def check_domain_patterns(domain: str) -> Optional[str]:
    """
    בדיקה מהירה של דפוסי דומיין - חוסך קריאות GPT
    מחזיר את הקטגוריה אם נמצאה התאמה, אחרת None
    """
    if not domain:
        return None
    
    domain_lower = domain.lower()
    
    for category, patterns in BLOCKED_PATTERNS.items():
        for pattern in patterns:
            if pattern in domain_lower:
                return category
    
    return None


async def classify_domain_with_gpt(
    domain: str,
    title: str = None,
    content: str = None,
    owner_info: dict = None
) -> Dict[str, Any]:
    """
    סיווג דומיין באמצעות GPT
    מחזיר: {type, reason, confidence, should_keep}
    """
    gpt = get_openai_client()
    
    system_prompt = """אתה מומחה בזיהוי סוגי עסקים לצורך שיתופי פעולה B2B.
המטרה: למצוא עסקים קטנים ואתרי לידים שנוכל להציע להם שיתוף פעולה.

קטגוריות (בחר אחת בלבד):
1. lead_site - אתר לידים, אפיליאייט, השוואות מחירים, הפניות ✅ לשמור
2. small_business - עסק קטן, יועץ, סוכן, משרד עו"ד/רו"ח, פרילנסר ✅ לשמור
3. content_site - בלוג, אתר תוכן (ניטרלי)
4. corporation - תאגיד גדול, חברה ציבורית ❌ לחסום
5. bank - בנק ❌ לחסום
6. insurance - חברת ביטוח ❌ לחסום
7. government - ממשלה, עירייה, רשות ❌ לחסום
8. academia - אוניברסיטה, מכללה, בית ספר ❌ לחסום
9. hospital - בית חולים, קופת חולים ❌ לחסום
10. nonprofit - עמותה, מלכ"ר ❌ לחסום
11. news - אתר חדשות, מדיה ❌ לחסום
12. religious - מוסד דתי, ישיבה ❌ לחסום
13. ecommerce_giant - איקומרס גדול (אמזון, עלי) ❌ לחסום
14. fintech - פינטק גדול ❌ לחסום
15. unknown - לא ניתן לקבוע

החזר JSON בלבד:
{"type": "category", "reason": "הסבר קצר בעברית", "confidence": 0.0-1.0}"""

    # Build context
    context_parts = [f"🌐 דומיין: {domain}"]
    if title:
        context_parts.append(f"📌 כותרת: {title}")
    if owner_info:
        if owner_info.get("email"):
            context_parts.append(f"✉️ מייל: {owner_info['email']}")
        if owner_info.get("org"):
            context_parts.append(f"🏢 ארגון: {owner_info['org']}")
    if content:
        # Limit content to 4000 chars
        context_parts.append(f"\n📄 תוכן:\n{content[:4000]}")
    
    user_prompt = "\n".join(context_parts)
    
    try:
        response, duration = await gpt.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=200
        )
        
        # Parse JSON
        try:
            result = json.loads(response)
        except:
            # Fallback parsing
            import re
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"type": "unknown", "reason": response[:200], "confidence": 0.5}
        
        # Add should_keep flag
        result["should_keep"] = result.get("type") in KEEP_CATEGORIES
        result["duration"] = duration
        
        return result
        
    except Exception as e:
        logger.error(f"GPT classification error for {domain}: {e}")
        return {
            "type": "error",
            "reason": str(e)[:200],
            "confidence": 0,
            "should_keep": False,
            "duration": 0
        }


async def run_global_classification(reset_existing: bool = True):
    """
    הפעלת תהליך הסיווג הגלובלי ברקע
    """
    global CLASSIFY_STATUS
    
    if CLASSIFY_STATUS["running"]:
        logger.warning("Classification already running!")
        return
    
    CLASSIFY_STATUS = {
        "running": True,
        "stopped": False,
        "phase": "initializing",
        "total": 0,
        "processed": 0,
        "pre_filtered": 0,
        "gpt_classified": 0,
        "kept": 0,
        "blocked": 0,
        "current_domain": "",
        "started_at": datetime.utcnow().isoformat(),
        "results_by_type": {}
    }
    
    try:
        async with AsyncSessionLocal() as session:
            # ========== Phase 1: Reset ==========
            if reset_existing:
                CLASSIFY_STATUS["phase"] = "reset"
                logger.info("🔄 Phase 1: Resetting existing classifications...")
                
                # Reset scan_queue
                await session.execute(
                    update(ScanQueue).values(
                        business_type=None,
                        business_type_reason=None,
                        ai_analyzed_at=None,
                        is_blacklisted=0
                    )
                )
                
                # Reset leads category
                await session.execute(
                    update(Lead).values(category=None)
                )
                
                await session.commit()
                logger.info("✅ Reset complete")
            
            # ========== Phase 2: Count items ==========
            CLASSIFY_STATUS["phase"] = "counting"
            
            # Count scan_queue items with content
            sq_count = await session.execute(
                select(func.count(ScanQueue.id)).where(ScanQueue.html_text != None)
            )
            scan_queue_total = sq_count.scalar() or 0
            
            # Count leads
            lead_count = await session.execute(select(func.count(Lead.id)))
            leads_total = lead_count.scalar() or 0
            
            CLASSIFY_STATUS["total"] = scan_queue_total + leads_total
            logger.info(f"📊 Total items: {CLASSIFY_STATUS['total']} (scan_queue: {scan_queue_total}, leads: {leads_total})")
            
            # ========== Phase 3: Pre-filter scan_queue ==========
            CLASSIFY_STATUS["phase"] = "pre_filter_scan_queue"
            logger.info("🚀 Phase 3: Pre-filtering scan_queue by domain patterns...")
            
            result = await session.execute(
                select(ScanQueue).where(ScanQueue.html_text != None)
            )
            scan_items = result.scalars().all()
            
            for item in scan_items:
                if CLASSIFY_STATUS["stopped"]:
                    logger.info("⏹️ Classification stopped by user")
                    break
                
                CLASSIFY_STATUS["current_domain"] = item.domain or ""
                
                # Check domain patterns first (fast)
                pattern_match = check_domain_patterns(item.domain)
                
                if pattern_match:
                    # Auto-classify by pattern
                    item.business_type = pattern_match
                    item.business_type_reason = f"סיווג אוטומטי לפי דפוס דומיין"
                    item.ai_analyzed_at = datetime.utcnow()
                    item.is_blacklisted = 1  # Auto-block
                    
                    CLASSIFY_STATUS["pre_filtered"] += 1
                    CLASSIFY_STATUS["blocked"] += 1
                    CLASSIFY_STATUS["results_by_type"][pattern_match] = \
                        CLASSIFY_STATUS["results_by_type"].get(pattern_match, 0) + 1
                    
                    logger.info(f"   🚫 Pre-filtered: {item.domain} → {pattern_match}")
                
                CLASSIFY_STATUS["processed"] += 1
                
                # Commit every 50 items
                if CLASSIFY_STATUS["processed"] % 50 == 0:
                    await session.commit()
            
            await session.commit()
            logger.info(f"✅ Pre-filter complete: {CLASSIFY_STATUS['pre_filtered']} blocked")
            
            # ========== Phase 4: GPT classify remaining scan_queue ==========
            if not CLASSIFY_STATUS["stopped"]:
                CLASSIFY_STATUS["phase"] = "gpt_scan_queue"
                logger.info("🤖 Phase 4: GPT classifying remaining scan_queue items...")
                
                result = await session.execute(
                    select(ScanQueue).where(
                        ScanQueue.html_text != None,
                        ScanQueue.business_type == None
                    )
                )
                remaining_items = result.scalars().all()
                
                for item in remaining_items:
                    if CLASSIFY_STATUS["stopped"]:
                        break
                    
                    CLASSIFY_STATUS["current_domain"] = item.domain or ""
                    
                    # Call GPT
                    gpt_result = await classify_domain_with_gpt(
                        domain=item.domain,
                        title=item.title,
                        content=item.html_text,
                        owner_info={
                            "email": item.owner_email,
                            "org": item.owner_org
                        }
                    )
                    
                    item.business_type = gpt_result.get("type", "unknown")
                    item.business_type_reason = gpt_result.get("reason", "")
                    item.ai_analyzed_at = datetime.utcnow()
                    
                    # Blacklist if not in keep categories
                    if not gpt_result.get("should_keep", False):
                        item.is_blacklisted = 1
                        CLASSIFY_STATUS["blocked"] += 1
                    else:
                        CLASSIFY_STATUS["kept"] += 1
                    
                    CLASSIFY_STATUS["gpt_classified"] += 1
                    CLASSIFY_STATUS["processed"] += 1
                    CLASSIFY_STATUS["results_by_type"][item.business_type] = \
                        CLASSIFY_STATUS["results_by_type"].get(item.business_type, 0) + 1
                    
                    emoji = "✅" if gpt_result.get("should_keep") else "🚫"
                    logger.info(f"   {emoji} GPT: {item.domain} → {item.business_type}")
                    
                    # Commit every 10 items
                    if CLASSIFY_STATUS["gpt_classified"] % 10 == 0:
                        await session.commit()
                
                await session.commit()
            
            # ========== Phase 5: Classify Leads ==========
            if not CLASSIFY_STATUS["stopped"]:
                CLASSIFY_STATUS["phase"] = "classify_leads"
                logger.info("🎯 Phase 5: Classifying leads...")
                
                result = await session.execute(select(Lead))
                leads = result.scalars().all()
                
                for lead in leads:
                    if CLASSIFY_STATUS["stopped"]:
                        break
                    
                    CLASSIFY_STATUS["current_domain"] = lead.domain or ""
                    
                    # Check domain patterns first
                    pattern_match = check_domain_patterns(lead.domain)
                    
                    if pattern_match:
                        lead.category = pattern_match
                        lead.status = "blacklisted"
                        CLASSIFY_STATUS["pre_filtered"] += 1
                        CLASSIFY_STATUS["blocked"] += 1
                    else:
                        # Check if we already classified this in scan_queue
                        sq_result = await session.execute(
                            select(ScanQueue).where(ScanQueue.domain == lead.domain).limit(1)
                        )
                        sq_item = sq_result.scalar_one_or_none()
                        
                        if sq_item and sq_item.business_type:
                            # Copy from scan_queue
                            lead.category = sq_item.business_type
                            if sq_item.business_type not in KEEP_CATEGORIES:
                                lead.status = "blacklisted"
                                CLASSIFY_STATUS["blocked"] += 1
                            else:
                                CLASSIFY_STATUS["kept"] += 1
                        else:
                            # Need GPT
                            ai_status = lead.ai_status or {}
                            gpt_result = await classify_domain_with_gpt(
                                domain=lead.domain,
                                title=lead.site_name,
                                content=ai_status.get("reasoning", ""),
                                owner_info=lead.contact_info
                            )
                            
                            lead.category = gpt_result.get("type", "unknown")
                            
                            if not gpt_result.get("should_keep", False):
                                lead.status = "blacklisted"
                                CLASSIFY_STATUS["blocked"] += 1
                            else:
                                CLASSIFY_STATUS["kept"] += 1
                            
                            CLASSIFY_STATUS["gpt_classified"] += 1
                    
                    CLASSIFY_STATUS["processed"] += 1
                    CLASSIFY_STATUS["results_by_type"][lead.category or "unknown"] = \
                        CLASSIFY_STATUS["results_by_type"].get(lead.category or "unknown", 0) + 1
                    
                    # Commit every 50 items
                    if CLASSIFY_STATUS["processed"] % 50 == 0:
                        await session.commit()
                
                await session.commit()
            
            # ========== Done ==========
            CLASSIFY_STATUS["phase"] = "completed"
            CLASSIFY_STATUS["current_domain"] = ""
            logger.info(f"🎉 Classification complete! Kept: {CLASSIFY_STATUS['kept']}, Blocked: {CLASSIFY_STATUS['blocked']}")
    
    except Exception as e:
        logger.error(f"❌ Classification error: {e}")
        CLASSIFY_STATUS["phase"] = f"error: {str(e)[:100]}"
    
    finally:
        CLASSIFY_STATUS["running"] = False


# ========== API Endpoints ==========

@router.post("/global-classify")
async def start_global_classification(
    background_tasks: BackgroundTasks,
    reset_existing: bool = Query(True, description="איפוס סיווגים קיימים"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    התחלת תהליך סיווג גלובלי של כל הדומיינים
    
    1. Pre-filter לפי דפוסי דומיין (חוסך קריאות GPT)
    2. GPT לשאר הדומיינים
    3. חסימה אוטומטית של קטגוריות לא רצויות
    """
    global CLASSIFY_STATUS
    
    if CLASSIFY_STATUS["running"]:
        return {
            "status": "already_running",
            "message": "תהליך סיווג כבר רץ",
            "progress": CLASSIFY_STATUS
        }
    
    # Start in background
    background_tasks.add_task(run_global_classification, reset_existing)
    
    return {
        "status": "started",
        "message": "תהליך הסיווג הגלובלי התחיל ברקע",
        "reset_existing": reset_existing
    }


@router.get("/global-classify/status")
async def get_classification_status():
    """קבלת סטטוס תהליך הסיווג"""
    return CLASSIFY_STATUS


@router.post("/global-classify/stop")
async def stop_classification():
    """עצירת תהליך הסיווג"""
    global CLASSIFY_STATUS
    
    if not CLASSIFY_STATUS["running"]:
        return {"status": "not_running", "message": "אין תהליך רץ"}
    
    CLASSIFY_STATUS["stopped"] = True
    return {"status": "stopping", "message": "שולח פקודת עצירה..."}


@router.get("/global-classify/results")
async def get_classification_results(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת תוצאות הסיווג"""
    
    # Count by business_type in scan_queue
    sq_result = await session.execute(
        select(ScanQueue.business_type, func.count(ScanQueue.id))
        .where(ScanQueue.business_type != None)
        .group_by(ScanQueue.business_type)
    )
    sq_counts = dict(sq_result.all())
    
    # Count by category in leads
    lead_result = await session.execute(
        select(Lead.category, func.count(Lead.id))
        .where(Lead.category != None)
        .group_by(Lead.category)
    )
    lead_counts = dict(lead_result.all())
    
    # Count blacklisted
    blacklisted_sq = await session.execute(
        select(func.count(ScanQueue.id)).where(ScanQueue.is_blacklisted == 1)
    )
    blacklisted_leads = await session.execute(
        select(func.count(Lead.id)).where(Lead.status == "blacklisted")
    )
    
    # Count kept
    kept_sq = await session.execute(
        select(func.count(ScanQueue.id)).where(
            ScanQueue.business_type.in_(KEEP_CATEGORIES),
            ScanQueue.is_blacklisted == 0
        )
    )
    kept_leads = await session.execute(
        select(func.count(Lead.id)).where(
            Lead.category.in_(KEEP_CATEGORIES),
            Lead.status != "blacklisted"
        )
    )
    
    return {
        "scan_queue": {
            "by_type": sq_counts,
            "total_blacklisted": blacklisted_sq.scalar() or 0,
            "total_kept": kept_sq.scalar() or 0
        },
        "leads": {
            "by_category": lead_counts,
            "total_blacklisted": blacklisted_leads.scalar() or 0,
            "total_kept": kept_leads.scalar() or 0
        },
        "keep_categories": KEEP_CATEGORIES,
        "block_categories": BLOCK_CATEGORIES,
        "last_run": CLASSIFY_STATUS.get("started_at"),
        "last_status": CLASSIFY_STATUS.get("phase")
    }


@router.get("/blocked-patterns")
async def get_blocked_patterns():
    """קבלת רשימת דפוסי הדומיינים החסומים"""
    return {
        "patterns": BLOCKED_PATTERNS,
        "keep_categories": KEEP_CATEGORIES,
        "block_categories": BLOCK_CATEGORIES
    }


@router.post("/test-domain/{domain}")
async def test_domain_classification(domain: str):
    """בדיקת סיווג דומיין יחיד (ללא שמירה)"""
    
    # Check pattern first
    pattern_match = check_domain_patterns(domain)
    
    if pattern_match:
        return {
            "domain": domain,
            "method": "pattern",
            "type": pattern_match,
            "should_keep": False,
            "reason": "התאמה לדפוס דומיין חסום"
        }
    
    # Call GPT
    result = await classify_domain_with_gpt(domain=domain)
    
    return {
        "domain": domain,
        "method": "gpt",
        **result
    }
