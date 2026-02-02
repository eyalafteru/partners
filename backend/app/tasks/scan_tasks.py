"""
PartnerCalc OS - Scan Tasks
משימות סריקה ברקע
"""
from celery import shared_task
from datetime import datetime
from loguru import logger
from urllib.parse import urlparse

from app.database import SyncSessionLocal
from app.models.scan_campaign import ScanCampaign, ScanQueue
from app.models.lead import Lead
from app.models.calculator import Calculator

# ========== Domain Pre-Filter Patterns ==========
# Copy from business_classifier.py for fast pre-filtering

BLOCKED_DOMAIN_PATTERNS = {
    "government": [".gov.il", "mof.gov", "health.gov", "edu.gov", "justice.gov", "municipality", "iriya"],
    "academia": [".ac.il", "university", "college", "technion", "weizmann", "tau.ac", "huji.ac", "bgu.ac"],
    "bank": ["leumi", "hapoalim", "discount", "mizrahi", "fibi", "bankisrael", "bank-of"],
    "insurance": ["harel", "migdal", "clal-ins", "phoenix", "menora", "ayalon", "fnx.co.il", "phenix"],
    "corporation": ["max.co.il", "isracard", "cal-online", "visa", "amex", "diners", "bezeq", "cellcom", "partner", "hot.net", "shlomo.co.il", "sixt", "gamaf.co.il", "eldan", "avis", "hertz", "budget"],
    "hospital": ["sheba", "ichilov", "hadassah", "rambam", "clalit", "maccabi", "meuhedet", "leumit", "hospital"],
    "news": ["ynet", "walla", "mako", "globes", "calcalist", "themarker", "israelhayom", "maariv", "haaretz", "n12.co.il"],
    "ecommerce_giant": ["amazon", "aliexpress", "ebay", "shufersal", "rami-levy", "zap.co.il", "ksp.co.il", "yad2.co.il", "winwin", "ivory"],
    "fintech": ["blender.co.il", "pepper.co.il", "paybox", "bit.co.il", "onezero", "5555.co.il", "555.co.il"],
}


def extract_base_domain(domain: str) -> str:
    """
    מחלץ דומיין בסיסי - מסיר subdomains
    loans.blender.co.il → blender.co.il
    www.example.co.il → example.co.il
    """
    if not domain:
        return domain
    
    domain = domain.lower().replace("www.", "")
    parts = domain.split(".")
    
    # Handle Israeli domains (.co.il, .org.il, .net.il, .ac.il, .gov.il)
    if len(parts) >= 3 and parts[-1] == "il" and parts[-2] in ["co", "org", "net", "ac", "gov", "muni", "k12"]:
        return ".".join(parts[-3:])
    
    # Handle .com, .org, .net, etc.
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    
    return domain


def get_existing_domains(session) -> set:
    """מחזיר את כל הדומיינים הקיימים ב-DB (כולל דומיינים בסיסיים)"""
    existing = session.query(ScanQueue.domain).all()
    domains = set()
    for (domain,) in existing:
        if domain:
            domains.add(domain.lower())
            domains.add(extract_base_domain(domain))
    return domains


def check_domain_blocked(domain: str) -> str | None:
    """בדיקה מהירה אם דומיין חסום לפי דפוס - מחזיר הקטגוריה או None"""
    if not domain:
        return None
    domain_lower = domain.lower()
    for category, patterns in BLOCKED_DOMAIN_PATTERNS.items():
        for pattern in patterns:
            if pattern in domain_lower:
                return category
    return None


@shared_task(bind=True)
def start_scan_campaign(self, campaign_id: int):
    """
    התחלת סריקה חדשה
    1. קריאה ל-Apify לקבלת URLs
    2. שמירה בתור
    3. התחלת עיבוד
    """
    session = SyncSessionLocal()
    
    try:
        # שליפת הקמפיין
        campaign = session.query(ScanCampaign).get(campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            return
        
        campaign.status = "running"
        campaign.started_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Starting scan campaign: {campaign.name}")
        
        # שלב 1: קבלת URLs מ-Apify
        from app.scraper.apify_client import ApifyGoogleScraper
        import asyncio
        
        apify = ApifyGoogleScraper()
        all_urls = []
        
        for keyword in campaign.keywords:
            try:
                # הרצה סינכרונית של async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                results = loop.run_until_complete(
                    apify.search(keyword, campaign.results_per_query or 100)
                )
                loop.close()
                
                all_urls.extend(results)
                logger.info(f"Found {len(results)} results for '{keyword}'")
                
            except Exception as e:
                logger.error(f"Apify search failed for '{keyword}': {e}")
        
        # 🚀 שליפת דומיינים קיימים מה-DB
        existing_domains = get_existing_domains(session)
        logger.info(f"Found {len(existing_domains)} existing domains in DB")
        
        # סינון כפילויות לפי דומיין (כולל בדיקה מול DB)
        seen_domains = set()
        unique_urls = []
        skipped_existing = 0
        skipped_subdomain = 0
        
        for result in all_urls:
            domain = result.get("domain", "").lower().replace("www.", "")
            if not domain:
                continue
            
            base_domain = extract_base_domain(domain)
            
            # בדיקה אם דומיין כבר קיים ב-DB
            if domain in existing_domains or base_domain in existing_domains:
                skipped_existing += 1
                continue
            
            # בדיקה אם הדומיין הבסיסי כבר נוסף בסריקה הזו
            if base_domain in seen_domains:
                skipped_subdomain += 1
                continue
            
            seen_domains.add(domain)
            seen_domains.add(base_domain)
            unique_urls.append(result)
        
        logger.info(f"Filtering: {skipped_existing} already in DB, {skipped_subdomain} subdomains, {len(unique_urls)} new unique")
        
        # שמירה בתור - עם Pre-filter לדומיינים חסומים
        pre_blocked = 0
        for result in unique_urls:
            domain = result.get("domain", "")
            blocked_category = check_domain_blocked(domain)
            
            queue_item = ScanQueue(
                campaign_id=campaign_id,
                url=result["url"],
                domain=domain,
                title=result.get("title"),
                description=result.get("description"),
                google_position=result.get("position"),
                status="pending"
            )
            
            # If blocked by pattern, mark immediately
            if blocked_category:
                queue_item.business_type = blocked_category
                queue_item.business_type_reason = "סיווג אוטומטי לפי דפוס דומיין"
                queue_item.is_blacklisted = 1
                queue_item.ai_analyzed_at = datetime.utcnow()
                pre_blocked += 1
            
            session.add(queue_item)
        
        campaign.total_urls = len(unique_urls)
        session.commit()
        
        logger.info(f"Added {len(unique_urls)} URLs to queue ({pre_blocked} pre-blocked by domain pattern)")
        
        # שלב 2: התחלת עיבוד
        process_scan_queue.delay(campaign_id)
        
    except Exception as e:
        logger.error(f"Scan campaign {campaign_id} failed: {e}")
        if campaign:
            campaign.status = "failed"
            session.commit()
        raise
        
    finally:
        session.close()


@shared_task(bind=True)
def process_scan_queue(self, campaign_id: int):
    """
    עיבוד תור הסריקות
    """
    session = SyncSessionLocal()
    
    try:
        campaign = session.query(ScanCampaign).get(campaign_id)
        if not campaign:
            return
        
        # קבלת כל המחשבונים
        calculators = session.query(Calculator).filter(Calculator.is_active == True).all()
        calcs_list = [
            {"id": c.id, "name": c.name, "intent_description": c.intent_description}
            for c in calculators
        ]
        
        # עיבוד התור
        while True:
            # בדיקה אם הסריקה הושהתה
            session.refresh(campaign)
            if campaign.status in ["paused", "completed", "failed"]:
                break
            
            # שליפת הפריט הבא
            item = session.query(ScanQueue).filter(
                ScanQueue.campaign_id == campaign_id,
                ScanQueue.status == "pending"
            ).first()
            
            if not item:
                break  # סיימנו
            
            item.status = "processing"
            session.commit()
            
            try:
                # סריקת האתר
                process_single_url(
                    session, 
                    item, 
                    campaign, 
                    calcs_list
                )
                
                item.status = "completed"
                item.processed_at = datetime.utcnow()
                campaign.scanned_count = (campaign.scanned_count or 0) + 1
                
            except Exception as e:
                logger.error(f"Failed to process {item.url}: {e}")
                item.status = "failed"
                item.error_message = str(e)[:500]
            
            session.commit()
        
        # סיום הסריקה
        campaign.status = "completed"
        campaign.completed_at = datetime.utcnow()
        session.commit()
        
        logger.info(f"Scan campaign {campaign.name} completed: "
                   f"{campaign.matched_count}/{campaign.scanned_count} matches")
        
    finally:
        session.close()


def process_single_url(session, queue_item: ScanQueue, campaign: ScanCampaign, calculators: list):
    """
    עיבוד URL בודד
    """
    import asyncio
    from urllib.parse import urlparse
    
    url = queue_item.url
    
    # חילוץ דומיין
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")
    
    # בדיקה אם הדומיין כבר קיים
    existing = session.query(Lead).filter(Lead.domain == domain).first()
    if existing:
        logger.info(f"Domain {domain} already exists, skipping")
        return
    
    # סריקת האתר
    from app.scraper.drission_scraper import StealthScraper
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    scraper = StealthScraper()
    scraped = loop.run_until_complete(scraper.scrape_site(url))
    
    if "error" in scraped:
        logger.warning(f"Scrape failed for {url}: {scraped['error']}")
        loop.close()
        return
    
    # ניתוח AI - האם עסק אמיתי?
    from app.ai.ollama_client import OllamaClient
    import json
    
    client = OllamaClient()
    
    # צומת 1: בדיקת עסק אמיתי
    is_real_response = loop.run_until_complete(
        client.generate(
            system_prompt="""אתה מזהה אתרי עסקים אמיתיים. 
            השב JSON: {"is_real": true/false, "confidence": 0.0-1.0, "reasoning": "הסבר"}""",
            user_prompt=f"האם האתר {domain} הוא עסק אמיתי? תוכן: {scraped['inner_text'][:2000]}",
            temperature=0.3
        )
    )
    
    try:
        is_real = json.loads(is_real_response)
    except:
        is_real = {"is_real": False, "confidence": 0, "reasoning": "Failed to parse"}
    
    if not is_real.get("is_real"):
        campaign.discarded_count = (campaign.discarded_count or 0) + 1
        logger.info(f"Discarded {domain}: not a real business")
        loop.close()
        return
    
    # צומת 2: התאמת מחשבון
    if calculators:
        match_response = loop.run_until_complete(
            client.generate(
                system_prompt="""בחר מחשבון מתאים. 
                השב JSON: {"calc_id": X, "match_score": 0.0-1.0, "reasoning": "הסבר"}""",
                user_prompt=f"מחשבונים: {json.dumps(calculators, ensure_ascii=False)}\n"
                           f"תוכן האתר: {scraped['inner_text'][:2000]}",
                temperature=0.3
            )
        )
        
        try:
            calc_match = json.loads(match_response)
            recommended_calc_id = calc_match.get("calc_id")
        except:
            recommended_calc_id = None
    else:
        recommended_calc_id = None
    
    loop.close()
    
    # יצירת ליד חדש
    lead = Lead(
        domain=domain,
        site_name=scraped.get("title"),
        category=campaign.category,
        contact_info={
            "emails": scraped.get("emails", []),
            "phones": scraped.get("phones", [])
        },
        ai_status={
            "is_real": True,
            "relevance_score": is_real.get("confidence", 0.5),
            "reasoning": is_real.get("reasoning", "")
        },
        status="matched",
        recommended_calc_id=recommended_calc_id,
        source_campaign_id=campaign.id,
        source_url=url,
        google_position=queue_item.google_position
    )
    
    session.add(lead)
    campaign.matched_count = (campaign.matched_count or 0) + 1
    
    logger.info(f"Created lead for {domain} with calc_id={recommended_calc_id}")
