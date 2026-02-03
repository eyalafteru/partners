"""
PartnerCalc OS - Pipeline Service
שירות אורקסטרציה לזרימת הסריקה המלאה
Apify -> ZenRows -> GPT Classification -> WHOIS -> Lead
"""
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import AsyncSessionLocal
from app.models.scan_campaign import ScanCampaign, ScanQueue, PipelineStage, PIPELINE_STAGE_LABELS
from app.models.lead import Lead
from app.scraper.whois_lookup import get_whois_lookup
from app.config import settings


# Global state for pipeline control
PIPELINE_STOP_FLAGS: Dict[int, bool] = {}  # scan_id -> should_stop
PIPELINE_ACTIVE: Dict[int, bool] = {}       # scan_id -> is_running


# Categories to auto-filter (not lead candidates)
FILTER_CATEGORIES = ["bank", "insurance", "corporation", "government", "fintech", "hospital", "academia", "news"]
KEEP_CATEGORIES = ["lead_site", "small_business"]


class PipelineService:
    """
    שירות Pipeline לעיבוד URLs מא' עד ת'
    """
    
    def __init__(self, session: AsyncSession = None):
        self.session = session
        self.max_concurrent = 5  # Process 5 URLs in parallel
        self.max_retries = 3
    
    async def run_pipeline(self, scan_id: int) -> Dict[str, Any]:
        """
        Run full pipeline for a scan campaign.
        This is called after Apify has collected URLs.
        
        Flow: ZenRows -> GPT Classification -> WHOIS -> Lead Creation
        """
        global PIPELINE_ACTIVE, PIPELINE_STOP_FLAGS
        
        if PIPELINE_ACTIVE.get(scan_id, False):
            return {"status": "already_running", "message": "Pipeline already running for this scan"}
        
        PIPELINE_ACTIVE[scan_id] = True
        PIPELINE_STOP_FLAGS[scan_id] = False
        
        try:
            async with AsyncSessionLocal() as session:
                # Get pending items
                result = await session.execute(
                    select(ScanQueue)
                    .where(ScanQueue.campaign_id == scan_id)
                    .where(ScanQueue.pipeline_stage < PipelineStage.LEAD_CREATED)
                    .where(ScanQueue.pipeline_stage != PipelineStage.FILTERED)
                    .where(ScanQueue.pipeline_stage != PipelineStage.FAILED)
                )
                items = result.scalars().all()
                
                if not items:
                    return {"status": "no_items", "message": "No items to process"}
                
                total = len(items)
                logger.info(f"🚀 Starting pipeline for scan {scan_id} with {total} items")
                
                # Update campaign status
                await session.execute(
                    update(ScanCampaign)
                    .where(ScanCampaign.id == scan_id)
                    .values(status="running")
                )
                await session.commit()
                
                # Process in batches of max_concurrent
                processed = 0
                leads_created = 0
                filtered = 0
                
                for i in range(0, total, self.max_concurrent):
                    if PIPELINE_STOP_FLAGS.get(scan_id, False):
                        logger.info(f"⏹️ Pipeline stopped by user for scan {scan_id}")
                        break
                    
                    batch = items[i:i + self.max_concurrent]
                    
                    # Process batch in parallel
                    tasks = [self.process_single_url(item.id) for item in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    for result in results:
                        if isinstance(result, dict):
                            if result.get("lead_created"):
                                leads_created += 1
                            if result.get("filtered"):
                                filtered += 1
                        processed += 1
                    
                    # Small delay between batches
                    await asyncio.sleep(0.5)
                
                # Update campaign status
                await session.execute(
                    update(ScanCampaign)
                    .where(ScanCampaign.id == scan_id)
                    .values(
                        status="completed" if not PIPELINE_STOP_FLAGS.get(scan_id) else "paused",
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()
                
                logger.info(f"✅ Pipeline complete for scan {scan_id}: {processed} processed, {leads_created} leads, {filtered} filtered")
                
                return {
                    "status": "completed",
                    "processed": processed,
                    "leads_created": leads_created,
                    "filtered": filtered
                }
                
        except Exception as e:
            logger.error(f"❌ Pipeline error for scan {scan_id}: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            PIPELINE_ACTIVE[scan_id] = False
    
    async def process_single_url(self, queue_id: int) -> Dict[str, Any]:
        """
        Process a single URL through the entire pipeline.
        Resumes from wherever it left off based on pipeline_stage.
        """
        async with AsyncSessionLocal() as session:
            # Get item
            result = await session.execute(
                select(ScanQueue).where(ScanQueue.id == queue_id)
            )
            item = result.scalar_one_or_none()
            
            if not item:
                return {"error": "Item not found"}
            
            try:
                stage = item.pipeline_stage or 0
                
                # Stage 0 -> 1: ZenRows Scraping
                if stage < PipelineStage.SCRAPED:
                    success = await self._scrape_content(session, item)
                    if not success:
                        return await self._handle_failure(session, item, "Scraping failed")
                
                # Stage 1 -> 2: GPT Classification
                if item.pipeline_stage < PipelineStage.CLASSIFIED:
                    success = await self._classify_business(session, item)
                    if not success:
                        return await self._handle_failure(session, item, "Classification failed")
                    
                    # Check if should be filtered
                    if item.business_type in FILTER_CATEGORIES:
                        item.pipeline_stage = PipelineStage.FILTERED
                        item.is_blacklisted = 1
                        item.stage_updated_at = datetime.utcnow()
                        await session.commit()
                        return {"filtered": True, "reason": item.business_type}
                
                # Stage 2 -> 3: WHOIS Lookup
                if item.pipeline_stage < PipelineStage.WHOIS_DONE:
                    await self._lookup_whois(session, item)
                    # WHOIS failure is not critical, continue anyway
                
                # Stage 3 -> 4: Lead Creation
                if item.pipeline_stage < PipelineStage.LEAD_CREATED:
                    lead_created = await self._create_lead(session, item)
                    if lead_created:
                        item.pipeline_stage = PipelineStage.LEAD_CREATED
                        item.stage_updated_at = datetime.utcnow()
                        await session.commit()
                        return {"lead_created": True}
                    else:
                        # No contact info, mark as filtered
                        item.pipeline_stage = PipelineStage.FILTERED
                        item.stage_updated_at = datetime.utcnow()
                        await session.commit()
                        return {"filtered": True, "reason": "No contact info"}
                
                return {"status": "completed"}
                
            except Exception as e:
                logger.error(f"Error processing {item.domain}: {e}")
                return await self._handle_failure(session, item, str(e))
    
    async def _scrape_content(self, session: AsyncSession, item: ScanQueue) -> bool:
        """Stage 1: Scrape content with ZenRows"""
        from app.scraper.zenrows_scraper import get_zenrows_scraper
        
        logger.info(f"📄 Scraping content: {item.domain}")
        
        try:
            scraper = get_zenrows_scraper()
            result = await scraper.scrape(item.url)
            
            if not result or result.get("error"):
                return False
            
            # Save scraped content
            item.html_text = result.get("inner_text", "")[:15000]
            item.html_body = result.get("html", "")[:50000]
            item.meta_title = result.get("title", "")
            item.meta_description = result.get("meta_description", "")
            item.nav_links = result.get("nav_links", [])
            item.has_menu_calculator = 1 if result.get("has_menu_calculator") else 0
            
            # Extract emails and phones from content
            if result.get("emails"):
                item.emails_found = result["emails"]
            if result.get("phones"):
                item.phones_found = result["phones"]
            
            # Update stage
            item.pipeline_stage = PipelineStage.SCRAPED
            item.stage_updated_at = datetime.utcnow()
            await session.commit()
            
            logger.info(f"✅ Scraped: {item.domain} ({len(item.html_text or '')} chars)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Scrape error {item.domain}: {e}")
            return False
    
    async def _classify_business(self, session: AsyncSession, item: ScanQueue) -> bool:
        """Stage 2: Classify business type with GPT"""
        from app.ai.openai_client import get_openai_client
        
        logger.info(f"🤖 Classifying: {item.domain}")
        
        try:
            gpt = get_openai_client()
            
            # System prompt for classification
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
8. government - ממשלתי / עירייה 🏛️
9. unknown - לא ידוע ❓

החזר JSON בלבד:
{"type": "lead_site/small_business/content_site/corporation/bank/insurance/fintech/government/unknown", "reason": "הסבר קצר"}"""
            
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
            
            # Call GPT
            response, duration = await gpt.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse response
            try:
                parsed = json.loads(response)
                item.business_type = parsed.get("type", "unknown")
                item.business_type_reason = parsed.get("reason", "")
            except:
                # Fallback: try to extract JSON
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
            item.pipeline_stage = PipelineStage.CLASSIFIED
            item.stage_updated_at = datetime.utcnow()
            
            # Auto-blacklist filtered categories
            if item.business_type in FILTER_CATEGORIES:
                item.is_blacklisted = 1
            else:
                item.is_blacklisted = 0
            
            await session.commit()
            
            emoji = {"lead_site": "🎯", "small_business": "💼", "content_site": "📰", 
                     "bank": "🏦", "insurance": "🛡️", "corporation": "🏢", "fintech": "🚀",
                     "government": "🏛️"}.get(item.business_type, "❓")
            logger.info(f"{emoji} Classified: {item.domain} -> {item.business_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Classification error {item.domain}: {e}")
            return False
    
    async def _lookup_whois(self, session: AsyncSession, item: ScanQueue) -> bool:
        """Stage 3: WHOIS lookup"""
        logger.info(f"📋 WHOIS lookup: {item.domain}")
        
        try:
            whois_client = get_whois_lookup()
            result = await whois_client.lookup(item.domain)
            
            if result.get("error"):
                logger.warning(f"WHOIS error for {item.domain}: {result['error']}")
                # Continue anyway, WHOIS is not critical
            else:
                # Save WHOIS data
                item.owner_name = result.get("registrant_name")
                item.owner_org = result.get("registrant_org")
                item.owner_email = result.get("registrant_email")
                item.owner_phone = result.get("registrant_phone")
                item.owner_address = result.get("address")
                item.owner_city = result.get("city")
                item.owner_country = result.get("country")
                item.registrar = result.get("registrar")
                item.domain_created = result.get("creation_date")
                item.domain_expires = result.get("expiration_date")
                item.whois_is_private = 1 if result.get("is_private") else 0
                item.whois_data = result
            
            item.whois_checked_at = datetime.utcnow()
            item.pipeline_stage = PipelineStage.WHOIS_DONE
            item.stage_updated_at = datetime.utcnow()
            await session.commit()
            
            has_contact = bool(item.owner_email or item.owner_phone)
            logger.info(f"{'✅' if has_contact else '⚠️'} WHOIS: {item.domain} - {'Has contact' if has_contact else 'No contact'}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ WHOIS error {item.domain}: {e}")
            # Mark as done anyway, WHOIS is optional
            item.pipeline_stage = PipelineStage.WHOIS_DONE
            item.stage_updated_at = datetime.utcnow()
            await session.commit()
            return True
    
    async def _create_lead(self, session: AsyncSession, item: ScanQueue) -> bool:
        """Stage 4: Create lead if has contact info"""
        
        # Check if has any contact info
        has_email = bool(item.owner_email or (item.emails_found and len(item.emails_found) > 0))
        has_phone = bool(item.owner_phone or (item.phones_found and len(item.phones_found) > 0))
        
        if not has_email and not has_phone:
            logger.info(f"⚠️ No contact info for {item.domain}, skipping lead creation")
            return False
        
        # Check if lead already exists
        existing = await session.execute(
            select(Lead).where(Lead.domain == item.domain)
        )
        if existing.scalar_one_or_none():
            logger.info(f"ℹ️ Lead already exists for {item.domain}")
            return True  # Consider as success
        
        # Get best email/phone
        best_email = item.owner_email
        if not best_email and item.emails_found:
            best_email = item.emails_found[0]
        
        best_phone = item.owner_phone
        if not best_phone and item.phones_found:
            best_phone = item.phones_found[0]
        
        # Create lead (email/phone are @property, accessed via contact_info)
        lead = Lead(
            domain=item.domain,
            site_name=item.owner_org or item.title or item.domain,
            category=item.business_type,
            contact_info={
                "emails": [best_email] if best_email else [],
                "phones": [best_phone] if best_phone else [],
                "whois_name": item.owner_name,
                "whois_org": item.owner_org,
            },
            source_campaign_id=item.campaign_id,
            status="new",
        )
        
        session.add(lead)
        
        # Update scan queue item status
        item.status = "matched"
        await session.commit()
        
        logger.info(f"✅ Lead created: {item.domain} ({best_email or best_phone})")
        return True
    
    async def _handle_failure(self, session: AsyncSession, item: ScanQueue, error: str) -> Dict[str, Any]:
        """Handle processing failure with retry logic"""
        item.retry_count = (item.retry_count or 0) + 1
        item.error_message = error
        item.stage_updated_at = datetime.utcnow()
        
        if item.retry_count >= self.max_retries:
            item.pipeline_stage = PipelineStage.FAILED
            logger.error(f"❌ Max retries reached for {item.domain}: {error}")
        else:
            logger.warning(f"⚠️ Retry {item.retry_count}/{self.max_retries} for {item.domain}: {error}")
        
        await session.commit()
        return {"error": error, "retry_count": item.retry_count}
    
    @staticmethod
    async def stop_pipeline(scan_id: int):
        """Stop a running pipeline"""
        global PIPELINE_STOP_FLAGS
        PIPELINE_STOP_FLAGS[scan_id] = True
        logger.info(f"⏹️ Stop signal sent to pipeline {scan_id}")
    
    @staticmethod
    async def is_pipeline_running(scan_id: int) -> bool:
        """Check if pipeline is running"""
        return PIPELINE_ACTIVE.get(scan_id, False)


async def resume_incomplete_pipelines():
    """
    Resume all incomplete pipelines on server startup.
    Called from main.py lifespan.
    """
    logger.info("🔄 Checking for incomplete pipelines to resume...")
    
    async with AsyncSessionLocal() as session:
        # Find scans that were running
        result = await session.execute(
            select(ScanCampaign)
            .where(ScanCampaign.status == "running")
        )
        running_scans = result.scalars().all()
        
        if not running_scans:
            logger.info("✅ No incomplete pipelines to resume")
            return
        
        logger.info(f"🔄 Found {len(running_scans)} scans to resume")
        
        for scan in running_scans:
            # Start pipeline in background
            asyncio.create_task(PipelineService().run_pipeline(scan.id))
            logger.info(f"🚀 Resumed pipeline for scan {scan.id}: {scan.name}")


def get_pipeline_service(session: AsyncSession = None) -> PipelineService:
    """Factory function to get PipelineService"""
    return PipelineService(session)
