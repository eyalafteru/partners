"""
PartnerCalc OS - Facebook Marketing Service
שירות מרכזי לניהול פרסום בקבוצות פייסבוק
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.models.facebook_marketing import (
    FacebookGroup,
    FacebookCampaign,
    FacebookPost,
    FacebookReply,
    FacebookConversation,
    FacebookMessage,
    FacebookPostTemplate
)
from app.models.post_strategy import PostStrategy
from app.models.calculator import Calculator
from app.services.post_generator_service import get_post_generator_service
from app.services.apify_service import get_apify_service
from app.services.facebook_reply_service import get_facebook_reply_service
from app.services.whatsapp_service import get_whatsapp_service
from app.services.local_browser_service import get_local_browser_service
from app.services.anti_spam_service import AntiSpamService
from app.services.facebook_action_logger import (
    fb_action_log,
    ACTION_POST, ACTION_REPLY, ACTION_SCRAPE_COMMENTS,
    METHOD_APIFY_POSTER, METHOD_APIFY_CUSTOM, METHOD_LOCAL_BROWSER,
)


class FacebookMarketingService:
    """שירות מרכזי לניהול פרסום בקבוצות פייסבוק"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.post_generator = get_post_generator_service()
        self.apify = get_apify_service()
        self.reply_bot = get_facebook_reply_service()
        self.whatsapp = get_whatsapp_service()
        self.anti_spam = AntiSpamService(session)
    
    # ========== Groups Management ==========
    
    async def get_groups(
        self,
        active_only: bool = True,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[FacebookGroup]:
        """קבלת רשימת קבוצות"""
        query = select(FacebookGroup)
        
        if active_only:
            query = query.where(FacebookGroup.is_active == True)
        
        if category:
            query = query.where(FacebookGroup.category == category)
        
        query = query.limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def add_group(
        self,
        fb_group_id: str,
        name: str,
        url: str = None,
        category: str = None,
        **kwargs
    ) -> FacebookGroup:
        """הוספת קבוצה חדשה"""
        group = FacebookGroup(
            fb_group_id=fb_group_id,
            name=name,
            url=url,
            category=category,
            **kwargs
        )
        self.session.add(group)
        await self.session.flush()
        
        logger.info(f"📁 ✅ Group added: {name}")
        return group
    
    async def search_and_add_groups(
        self,
        search_query: str,
        max_groups: int = 20,
        category: str = None
    ) -> List[FacebookGroup]:
        """חיפוש קבוצות ב-Apify והוספה למערכת"""
        groups_data = await self.apify.search_groups(
            search_query=search_query,
            max_groups=max_groups
        )
        
        if not groups_data:
            return []
        
        added_groups = []
        
        for data in groups_data:
            # בדיקה אם הקבוצה כבר קיימת
            fb_group_id = data.get("groupId") or data.get("id")
            if not fb_group_id:
                continue
            
            existing = await self.session.execute(
                select(FacebookGroup).where(FacebookGroup.fb_group_id == fb_group_id)
            )
            if existing.scalar_one_or_none():
                continue
            
            group = await self.add_group(
                fb_group_id=fb_group_id,
                name=data.get("name", ""),
                url=data.get("url", ""),
                member_count=data.get("memberCount", 0),
                category=category,
                description=data.get("description", ""),
                synced_at=datetime.utcnow()
            )
            added_groups.append(group)
        
        logger.info(f"📁 ✅ Added {len(added_groups)} groups from search")
        return added_groups
    
    # ========== Campaign Management ==========
    
    async def create_campaign(
        self,
        name: str,
        topic: str,
        target_group_ids: List[int],
        image_percentage: int = 50,
        template_id: int = None,
        **kwargs
    ) -> FacebookCampaign:
        """יצירת קמפיין חדש"""
        campaign = FacebookCampaign(
            name=name,
            topic=topic,
            target_group_ids=target_group_ids,
            image_percentage=image_percentage,
            template_id=template_id,
            status="draft",
            **kwargs
        )
        self.session.add(campaign)
        await self.session.flush()
        
        logger.info(f"🚀 ✅ Campaign created: {name}")
        return campaign
    
    async def get_campaign(self, campaign_id: int) -> Optional[FacebookCampaign]:
        """קבלת קמפיין לפי ID"""
        result = await self.session.execute(
            select(FacebookCampaign).where(FacebookCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def generate_campaign_posts(self, campaign_id: int) -> List[FacebookPost]:
        """יצירת פוסטים לקמפיין - משתמש באסטרטגיות ומחשבונים!"""
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # עדכון סטטוס
        campaign.status = "generating"
        await self.session.flush()
        
        # קבלת קבוצות היעד
        groups = await self.session.execute(
            select(FacebookGroup).where(
                FacebookGroup.id.in_(campaign.target_group_ids)
            )
        )
        groups = groups.scalars().all()
        
        if not groups:
            raise ValueError("No target groups found")
        
        # 🎯 קבלת אסטרטגיות מהקמפיין
        strategies = []
        strategy_ids = campaign.strategy_ids or []
        if strategy_ids:
            strat_result = await self.session.execute(
                select(PostStrategy).where(
                    PostStrategy.id.in_(strategy_ids),
                    PostStrategy.is_active == True
                )
            )
            strategies = strat_result.scalars().all()
            logger.info(f"📋 Found {len(strategies)} strategies for campaign: {[s.name for s in strategies]}")
        
        # 🧮 קבלת מחשבון מהקמפיין
        calculator = None
        if campaign.calculator_id:
            calc_result = await self.session.execute(
                select(Calculator).where(Calculator.id == campaign.calculator_id)
            )
            calculator = calc_result.scalar_one_or_none()
            if calculator:
                logger.info(f"🧮 Using calculator: {calculator.name}")
        
        # קבלת תבנית אם יש
        base_template = ""
        if campaign.template_id:
            template = await self.session.execute(
                select(FacebookPostTemplate).where(
                    FacebookPostTemplate.id == campaign.template_id
                )
            )
            template = template.scalar_one_or_none()
            if template:
                base_template = template.base_content
        
        # יצירת פוסטים - משתמשים באסטרטגיות!
        posts = []
        include_first_comment = campaign.link_placement == "first_comment"
        
        for i, group in enumerate(groups):
            # בחירת אסטרטגיה (רוטציה בין האסטרטגיות)
            strategy = strategies[i % len(strategies)] if strategies else None
            
            if strategy and calculator:
                # ✨ יצירה עם אסטרטגיה ומחשבון
                logger.info(f"📝 Generating with strategy '{strategy.name}' for group '{group.name}'")
                
                # שליפת פוסטים קודמים לקבוצה הזו (כדי שה-AI לא יחזור על עצמו)
                prev_posts_result = await self.session.execute(
                    select(FacebookPost.content)
                    .where(
                        and_(
                            FacebookPost.group_id == group.id,
                            FacebookPost.content.isnot(None),
                            FacebookPost.content != ""
                        )
                    )
                    .order_by(FacebookPost.created_at.desc())
                    .limit(5)
                )
                previous_posts = [row[0] for row in prev_posts_result.all()]
                
                gen_result = await self.post_generator.generate_strategic_post(
                    calculator_name=calculator.name,
                    calculator_url=calculator.target_url or "",
                    calculator_summary=calculator.ai_summary or calculator.intent_description or "",
                    strategy_system_prompt=strategy.system_prompt or "",
                    strategy_post_template=strategy.post_template or "",
                    group_name=group.name,
                    group_category=group.category or "",
                    group_description=group.description or "",
                    previous_posts=previous_posts,
                    include_first_comment=include_first_comment
                )
                
                # הכנת תוכן הפוסט עם לינק YouTube אם צריך
                post_content = gen_result.get("post_content") or ""
                youtube_url = None
                
                # בדיקה אם צריך לכלול וידאו
                media_pref = campaign.media_preference or "image"
                if media_pref in ["video", "both"] and calculator.youtube_url:
                    youtube_url = calculator.youtube_url
                    # הוספת לינק YouTube לתוכן הפוסט אם הוא לא קיים כבר
                    if youtube_url not in post_content:
                        post_content = f"{post_content}\n\n🎥 צפה בהדגמה:\n{youtube_url}"
                
                # 🐞 DEBUG: שמירת הפרומפט המלא
                debug_prompt = gen_result.get("debug_full_prompt", "")
                if gen_result.get("debug_system_message"):
                    debug_prompt = f"=== SYSTEM MESSAGE ===\n{gen_result.get('debug_system_message')}\n\n=== USER PROMPT ===\n{debug_prompt}"
                
                post = FacebookPost(
                    campaign_id=campaign.id,
                    group_id=group.id,
                    content=post_content,
                    first_comment_content=gen_result.get("first_comment_content"),
                    calculator_id=calculator.id,
                    strategy_id=strategy.id,
                    youtube_url=youtube_url,
                    status="pending_approval" if post_content else "failed",
                    debug_ai_prompt=debug_prompt if debug_prompt else None  # 🐞 DEBUG
                )
                
                # עדכון מונה שימוש באסטרטגיה
                strategy.times_used = (strategy.times_used or 0) + 1
                
            else:
                # יצירה רגילה (ללא אסטרטגיה)
                logger.info(f"📝 Generating without strategy for group '{group.name}'")
                
                gen_posts = await self.post_generator.generate_campaign_posts(
                    topic=campaign.topic,
                    groups=[{"id": group.id, "name": group.name}],
                    image_percentage=campaign.image_percentage,
                    base_template=base_template,
                    target_audience=campaign.target_audience or ""
                )
                
                gen_post = gen_posts[0] if gen_posts else {}
                post = FacebookPost(
                    campaign_id=campaign.id,
                    group_id=group.id,
                    content=gen_post.get("content", ""),
                    has_image=gen_post.get("has_image", False),
                    image_prompt=gen_post.get("image_prompt"),
                    image_url=gen_post.get("image_url"),
                    status="pending_approval" if gen_post.get("content") else "failed"
                )
            
            self.session.add(post)
            posts.append(post)
        
        # עדכון קמפיין
        campaign.status = "ready"
        campaign.total_posts_generated = len(posts)
        
        await self.session.flush()
        
        logger.info(f"📝 ✅ Generated {len(posts)} posts for campaign: {campaign.name}")
        return posts
    
    async def generate_single_post(self, campaign_id: int, group_id: int) -> Optional[FacebookPost]:
        """יצירת פוסט בודד לקבוצה בקמפיין - משתמש באסטרטגיות!"""
        campaign = await self.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign {campaign_id} not found")
        
        # קבלת הקבוצה
        group_result = await self.session.execute(
            select(FacebookGroup).where(FacebookGroup.id == group_id)
        )
        group = group_result.scalar_one_or_none()
        if not group:
            raise ValueError(f"Group {group_id} not found")
        
        # 🎯 קבלת אסטרטגיה אקראית מהקמפיין
        strategy = None
        strategy_ids = campaign.strategy_ids or []
        if strategy_ids:
            import random
            random_strategy_id = random.choice(strategy_ids)
            strat_result = await self.session.execute(
                select(PostStrategy).where(
                    PostStrategy.id == random_strategy_id,
                    PostStrategy.is_active == True
                )
            )
            strategy = strat_result.scalar_one_or_none()
            if strategy:
                logger.info(f"📋 Using strategy: {strategy.name}")
        
        # 🧮 קבלת מחשבון מהקמפיין
        calculator = None
        if campaign.calculator_id:
            calc_result = await self.session.execute(
                select(Calculator).where(Calculator.id == campaign.calculator_id)
            )
            calculator = calc_result.scalar_one_or_none()
        
        # קבלת פוסטים קודמים לקבוצה זו (להימנע מחזרות)
        prev_posts_result = await self.session.execute(
            select(FacebookPost.content).where(
                FacebookPost.group_id == group_id,
                FacebookPost.campaign_id == campaign_id
            ).limit(5)
        )
        previous_posts = [p[0] for p in prev_posts_result.fetchall() if p[0]]
        
        include_first_comment = campaign.link_placement == "first_comment"
        content = None
        first_comment_content = None
        strategy_id = None
        calculator_id = None
        debug_ai_prompt = None  # 🐞 DEBUG
        
        if strategy and calculator:
            # ✨ יצירה עם אסטרטגיה ומחשבון
            logger.info(f"📝 Generating with strategy '{strategy.name}' and calculator '{calculator.name}'")
            
            gen_result = await self.post_generator.generate_strategic_post(
                calculator_name=calculator.name,
                calculator_url=calculator.target_url or "",
                calculator_summary=calculator.ai_summary or calculator.intent_description or "",
                strategy_system_prompt=strategy.system_prompt or "",
                strategy_post_template=strategy.post_template or "",
                group_name=group.name,
                previous_posts=previous_posts,
                include_first_comment=include_first_comment
            )
            
            content = gen_result.get("post_content")
            first_comment_content = gen_result.get("first_comment_content")
            strategy_id = strategy.id
            calculator_id = calculator.id
            
            # 🐞 DEBUG: שמירת הפרומפט המלא
            debug_prompt = gen_result.get("debug_full_prompt", "")
            if gen_result.get("debug_system_message"):
                debug_ai_prompt = f"=== SYSTEM MESSAGE ===\n{gen_result.get('debug_system_message')}\n\n=== USER PROMPT ===\n{debug_prompt}"
            else:
                debug_ai_prompt = debug_prompt
            
            # עדכון מונה שימוש באסטרטגיה
            strategy.times_used = (strategy.times_used or 0) + 1
        else:
            # יצירה רגילה (ללא אסטרטגיה)
            # קבלת תבנית אם יש
            base_template = ""
            if campaign.template_id:
                template_result = await self.session.execute(
                    select(FacebookPostTemplate).where(
                        FacebookPostTemplate.id == campaign.template_id
                    )
                )
                template = template_result.scalar_one_or_none()
                if template:
                    base_template = template.base_content
            
            content = await self.post_generator.generate_post_variation(
                topic=campaign.topic,
                group_name=group.name,
                target_audience=campaign.target_audience or "",
                base_template=base_template,
                previous_posts=previous_posts
            )
        
        if not content:
            return None
        
        # בדיקה אם צריך תמונה
        has_image = False
        image_prompt = None
        image_url = None
        
        if campaign.image_percentage > 0:
            import random
            if random.randint(1, 100) <= campaign.image_percentage:
                has_image = True
                # יצירת תמונה
                image_prompt = await self.post_generator.generate_viral_image_prompt(
                    post_content=content,
                    style="eyal"
                )
                if image_prompt:
                    from app.services.replicate_service import get_replicate_service
                    replicate = get_replicate_service()
                    image_url = await replicate.generate_post_image(image_prompt, use_lora=True)
        
        # בדיקה אם צריך לכלול וידאו
        youtube_url = None
        media_pref = campaign.media_preference or "image"
        if media_pref in ["video", "both"] and calculator and calculator.youtube_url:
            youtube_url = calculator.youtube_url
            # הוספת לינק YouTube לתוכן הפוסט אם הוא לא קיים כבר
            if youtube_url not in content:
                content = f"{content}\n\n🎥 צפה בהדגמה:\n{youtube_url}"
        
        # יצירת הפוסט ב-DB
        post = FacebookPost(
            campaign_id=campaign.id,
            group_id=group_id,
            content=content,
            has_image=has_image,
            image_prompt=image_prompt,
            image_url=image_url,
            youtube_url=youtube_url,
            first_comment_content=first_comment_content,
            calculator_id=calculator_id,
            strategy_id=strategy_id,
            status="pending_approval",
            debug_ai_prompt=debug_ai_prompt if debug_ai_prompt else None  # 🐞 DEBUG
        )
        self.session.add(post)
        
        # עדכון מונה קמפיין
        campaign.total_posts_generated += 1
        
        logger.info(f"📝 ✅ Generated single post for group: {group.name}")
        return post
    
    # ========== Posts Management ==========
    
    async def get_pending_posts(self, campaign_id: int = None) -> List[FacebookPost]:
        """קבלת פוסטים ממתינים לאישור"""
        query = select(FacebookPost).where(
            FacebookPost.status == "pending_approval"
        )
        
        if campaign_id:
            query = query.where(FacebookPost.campaign_id == campaign_id)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def approve_post(self, post_id: int) -> FacebookPost:
        """אישור פוסט"""
        result = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        post.status = "approved"
        post.approved_at = datetime.utcnow()
        
        # עדכון קמפיין
        if post.campaign_id:
            campaign = await self.get_campaign(post.campaign_id)
            if campaign:
                campaign.total_posts_approved += 1
        
        await self.session.flush()
        
        logger.info(f"✅ Post {post_id} approved")
        return post
    
    async def reject_post(self, post_id: int, reason: str = None) -> FacebookPost:
        """דחיית פוסט"""
        result = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        post.status = "rejected"
        post.rejection_reason = reason
        
        await self.session.flush()
        
        logger.info(f"❌ Post {post_id} rejected")
        return post
    
    async def publish_post(self, post_id: int) -> FacebookPost:
        """פרסום פוסט"""
        result = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post:
            raise ValueError(f"Post {post_id} not found")
        
        if post.status not in ("approved", "failed"):
            raise ValueError(f"Post {post_id} is not approved or failed (current: {post.status})")
        
        # קבלת הקבוצה
        group = await self.session.execute(
            select(FacebookGroup).where(FacebookGroup.id == post.group_id)
        )
        group = group.scalar_one_or_none()
        
        if not group or not group.url:
            post.status = "failed"
            post.publish_error = "Group URL not found"
            await self.session.flush()
            return post
        
        # בדיקת Anti-Spam
        can_post, reason = await self.anti_spam.can_post_to_group(post.group_id)
        if not can_post:
            post.status = "approved"  # חזרה לסטטוס מאושר להמתנה
            post.publish_error = reason
            await self.session.flush()
            logger.warning(f"📤 ⏳ Post {post_id} delayed: {reason}")
            return post
        
        # פרסום דרך Apify
        post.status = "publishing"
        await self.session.flush()
        
        run_info = await self.apify.post_single(
            group_url=group.url,
            message=post.content
        )
        
        if run_info:
            run_id = run_info.get("id")
            post.apify_run_id = run_id
            
            # המתנה לסיום הריצה
            logger.info(f"📤 Waiting for Apify run {run_id} to complete...")
            final_status = await self.apify.wait_for_run(run_id, max_wait_seconds=180)
            
            if final_status and final_status.get("status") == "SUCCEEDED":
                # שליפת תוצאות
                dataset = await self.apify.get_run_dataset(run_id)
                logger.info(f"📤 Apify dataset results: {dataset}")
                
                # בדיקה אם הפוסט באמת הצליח - חיפוש סיבות כישלון בתוצאות
                failure_reason = self._check_for_failure_in_results(dataset)
                if failure_reason:
                    post.status = "failed"
                    post.publish_error = f"Apify: {failure_reason}"
                    logger.error(f"📤 ❌ Post {post_id} failed inside Apify: {failure_reason}")
                    await self.session.flush()
                    return post
                
                # ניסיון לחלץ URL הפוסט מהתוצאות
                fb_post_url = self._extract_post_url_from_results(dataset, group.url)
                if fb_post_url:
                    post.fb_post_url = fb_post_url
                    logger.info(f"📤 Extracted post URL: {fb_post_url}")
                else:
                    # אם אין URL בתוצאות, ננסה לבנות אחד מ-group URL
                    logger.warning(f"📤 Could not extract post URL from Apify results")
                
                post.status = "published"
                post.publish_error = None  # ניקוי שגיאות ישנות
                post.published_at = datetime.utcnow()
                
                # עדכון קבוצה
                group.total_posts += 1
                group.last_post_at = datetime.utcnow()
                
                # עדכון קמפיין
                if post.campaign_id:
                    campaign = await self.get_campaign(post.campaign_id)
                    if campaign:
                        campaign.total_posts_published += 1
                
                logger.info(f"📤 ✅ Post {post_id} published successfully")
            else:
                # הריצה נכשלה
                status_str = final_status.get("status") if final_status else "UNKNOWN"
                post.status = "failed"
                post.publish_error = f"Apify run ended with status: {status_str}"
                logger.error(f"📤 ❌ Post {post_id} publish failed - Apify status: {status_str}")
        else:
            post.status = "failed"
            post.publish_error = "Failed to start Apify run"
            logger.error(f"📤 ❌ Post {post_id} publish failed - could not start Apify run")
        
        await self.session.flush()
        return post
    
    def _check_for_failure_in_results(self, dataset: list) -> Optional[str]:
        """
        בדיקה אם הפוסט נכשל בתוך תוצאות Apify
        תומך גם באקטור הישן (bhansalisoft) וגם באקטור המותאם אישית
        
        Args:
            dataset: תוצאות מ-Apify
            
        Returns:
            סיבת הכישלון או None אם הצליח
        """
        if not dataset:
            return "No results from Apify"
        
        for item in dataset:
            # בדיקת סטטוס תחילה (תומך באקטור המותאם: success, failed, cookie_expired, blocked)
            # חשוב: אם הסטטוס הוא success, מתעלמים משדה error (יכול להכיל הערות שאינן שגיאה)
            status = item.get("status") or item.get("Status")
            
            if status and status.lower() == "success":
                # הפוסט הצליח - אין כישלון
                continue
            
            if status and status.lower() in ["failed", "error", "blocked", "cookie_expired"]:
                reason = item.get("error") or item.get("message") or item.get("reason") or status
                if status.lower() == "cookie_expired":
                    logger.error("🍪 ❌ COOKIE EXPIRED! יש לעדכן את ה-Cookie דרך המערכת")
                    return "Cookie פייסבוק פג תוקף - יש לעדכן Cookie חדש דרך המערכת"
                if status.lower() == "blocked":
                    logger.error("🚫 BLOCKED by Facebook!")
                    return f"חסום על ידי פייסבוק: {reason}"
                return str(reason)
            
            # בדיקת שדות כישלון נפוצים (רק אם אין שדה status ברור)
            for fail_field in ["Failed_Reason", "failed_reason", "failedReason", "error", "Error", "errorMessage"]:
                if fail_field in item and item[fail_field]:
                    return str(item[fail_field])
            
            # בדיקה ספציפית ל-bhansalisoft actor
            if item.get("Posted") == False or item.get("posted") == False:
                reason = item.get("Failed_Reason") or item.get("message") or "Post failed"
                return str(reason)
        
        return None
    
    def _extract_post_url_from_results(
        self, 
        dataset: list, 
        group_url: str
    ) -> Optional[str]:
        """
        חילוץ URL הפוסט מתוצאות Apify
        
        Args:
            dataset: תוצאות מ-Apify
            group_url: URL הקבוצה
            
        Returns:
            URL הפוסט או None
        """
        if not dataset:
            return None
        
        # ניסיון לחלץ URL מהתוצאות (תלוי בפורמט של ה-Actor)
        for item in dataset:
            # ניסיון שדות נפוצים
            for field in ["postUrl", "post_url", "url", "postLink", "link", "permalink"]:
                if field in item and item[field]:
                    return item[field]
            
            # בדיקה אם יש post_id שניתן לבנות ממנו URL
            for id_field in ["postId", "post_id", "id"]:
                if id_field in item and item[id_field]:
                    post_id = item[id_field]
                    # בניית URL מ-post_id וקבוצה
                    if "groups" in group_url:
                        return f"{group_url.rstrip('/')}/posts/{post_id}"
        
        return None
    
    # ========== Replies Management ==========
    
    async def sync_post_comments(self, post_id: int) -> List[FacebookReply]:
        """סנכרון תגובות לפוסט - כולל ניתוח AI ויצירת הצעת תגובה"""
        result = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == post_id)
        )
        post = result.scalar_one_or_none()
        
        if not post or not post.fb_post_url:
            return []
        
        # סריקת תגובות
        comments = await self.apify.get_post_comments(post.fb_post_url)
        
        if not comments:
            return []
        
        # זיהוי שמות פרופיל שלנו כדי לדלג על תגובות שלנו
        from app.config import settings as current_settings
        own_names_raw = current_settings.fb_own_profile_names or ""
        own_names = {name.strip().lower() for name in own_names_raw.split(",") if name.strip()}
        
        new_replies = []
        post_context = (post.content or "")[:200]
        
        for comment in comments:
            fb_comment_id = comment.get("id") or comment.get("commentId")
            message = (comment.get("text") or "").strip()
            commenter_name = (comment.get("profileName") or "").strip()
            
            # דילוג על תגובות ריקות
            if not message:
                continue
            
            # יצירת ID אם אין (עבור custom scraper)
            if not fb_comment_id:
                import hashlib
                fb_comment_id = f"pw_{hashlib.md5(f'{commenter_name}:{message[:50]}'.encode()).hexdigest()[:20]}"
            
            # דילוג על תגובות של בעל החשבון (תגובות שלנו)
            if commenter_name.lower() in own_names:
                logger.debug(f"💬 Skipping own comment from '{commenter_name}'")
                continue
            
            # בדיקה אם כבר קיים (idempotency) - לפי ID
            existing = await self.session.execute(
                select(FacebookReply).where(
                    FacebookReply.fb_comment_id == fb_comment_id
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # בדיקה נוספת: שם + טקסט (למניעת כפילויות בין scraper-ים שונים)
            existing_by_text = await self.session.execute(
                select(FacebookReply).where(
                    FacebookReply.post_id == post.id,
                    FacebookReply.fb_user_name == commenter_name,
                    FacebookReply.message == message
                )
            )
            if existing_by_text.scalar_one_or_none():
                continue
            
            # ניתוח מלא: analyze + generate response בקריאה אחת
            try:
                process_result = await self.reply_bot.process_reply(
                    message=message,
                    post_context=post_context
                )
                analysis = process_result.get("analysis", {})
                suggested_response = process_result.get("suggested_response")
                suggested_channel = process_result.get("suggested_channel", "comment")
                initial_status = "ai_suggested" if suggested_response else "new"
            except Exception as e:
                logger.warning(f"💬 ⚠️ AI processing failed for comment {fb_comment_id}: {e}")
                analysis = {}
                suggested_response = None
                suggested_channel = None
                initial_status = "new"
            
            reply = FacebookReply(
                post_id=post.id,
                fb_comment_id=fb_comment_id,
                fb_user_id=comment.get("profileId"),
                fb_user_name=comment.get("profileName"),
                fb_user_profile_url=comment.get("profileUrl"),
                fb_user_profile_pic=comment.get("profilePicture"),
                message=message,
                ai_detected_intent=analysis.get("intent"),
                ai_intent_confidence=None,
                wants_private=analysis.get("wants_private", False),
                ai_analysis=analysis,
                suggested_response=suggested_response,
                suggested_channel=suggested_channel,
                status=initial_status,
                received_at=datetime.utcnow()
            )
            self.session.add(reply)
            new_replies.append(reply)
        
        # עדכון ספירה
        post.replies_count = (post.replies_count or 0) + len(new_replies)
        
        await self.session.flush()
        
        # שליחת התראות WhatsApp על תגובות חדשות -- מושבת זמנית
        # if new_replies:
        #     group_result = await self.session.execute(
        #         select(FacebookGroup).where(FacebookGroup.id == post.group_id)
        #     )
        #     group = group_result.scalar_one_or_none()
        #     group_name = group.name if group else "קבוצה לא ידועה"
        #     
        #     for reply in new_replies:
        #         try:
        #             interest = (reply.ai_analysis or {}).get("interest_level", "")
        #             await self.whatsapp.send_facebook_comment_alert(
        #                 group_name=group_name,
        #                 commenter_name=reply.fb_user_name or "משתמש",
        #                 comment_text=reply.message or "",
        #                 suggested_response=reply.suggested_response,
        #                 post_id=post.id,
        #                 interest_level=interest
        #             )
        #         except Exception as e:
        #             logger.warning(f"💬 ⚠️ Failed to send WhatsApp alert: {e}")
        
        logger.info(f"💬 ✅ Synced {len(new_replies)} new replies for post {post_id}")
        return new_replies
    
    async def get_pending_replies(self) -> List[FacebookReply]:
        """קבלת תגובות ממתינות לטיפול (כולל הצעות AI שמחכות לאישור)"""
        result = await self.session.execute(
            select(FacebookReply).where(
                FacebookReply.status.in_(["new", "pending_response", "ai_suggested"])
            ).order_by(FacebookReply.created_at.desc())
        )
        return result.scalars().all()
    
    async def get_reply_stats(self) -> dict:
        """סטטיסטיקות תגובות"""
        from datetime import timedelta
        
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # ספירות לפי סטטוס
        total_result = await self.session.execute(
            select(func.count(FacebookReply.id))
        )
        total = total_result.scalar_one() or 0
        
        pending_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.status.in_(["new", "ai_suggested", "pending_response"])
            )
        )
        pending = pending_result.scalar_one() or 0
        
        responded_today_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                and_(
                    FacebookReply.status == "responded",
                    FacebookReply.responded_at >= today
                )
            )
        )
        responded_today = responded_today_result.scalar_one() or 0
        
        ai_suggested_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.status == "ai_suggested"
            )
        )
        ai_suggested = ai_suggested_result.scalar_one() or 0
        
        responded_total_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.status == "responded"
            )
        )
        responded_total = responded_total_result.scalar_one() or 0
        
        ignored_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.status == "ignored"
            )
        )
        ignored = ignored_result.scalar_one() or 0
        
        # תגובות שהתקבלו היום
        new_today_result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.created_at >= today
            )
        )
        new_today = new_today_result.scalar_one() or 0
        
        # פירוט לפי intent
        intent_result = await self.session.execute(
            select(
                FacebookReply.ai_detected_intent,
                func.count(FacebookReply.id)
            ).where(
                FacebookReply.ai_detected_intent.isnot(None)
            ).group_by(FacebookReply.ai_detected_intent)
        )
        intent_breakdown = {row[0]: row[1] for row in intent_result.all()}
        
        return {
            "total": total,
            "pending_approval": pending,
            "ai_suggested": ai_suggested,
            "responded_today": responded_today,
            "responded_total": responded_total,
            "ignored": ignored,
            "new_today": new_today,
            "intent_breakdown": intent_breakdown
        }
    
    async def generate_reply_response(self, reply_id: int) -> FacebookReply:
        """יצירת תשובה מוצעת לתגובה"""
        logger.info(f"💬 generate_reply_response: reply_id={reply_id}, AI configured={self.reply_bot.is_configured}")
        if not self.reply_bot.is_configured:
            raise ValueError(
                "לא הוגדר מפתח AI. הוסף OPENAI_API_KEY או ANTHROPIC_API_KEY לקובץ .env בתיקיית backend."
            )
        result = await self.session.execute(
            select(FacebookReply).where(FacebookReply.id == reply_id)
        )
        reply = result.scalar_one_or_none()
        
        if not reply:
            raise ValueError(f"Reply {reply_id} not found")
        
        # קבלת הקשר הפוסט
        post = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == reply.post_id)
        )
        post = post.scalar_one_or_none()
        
        # יצירת תשובה
        logger.info(f"💬 Calling AI process_reply for reply {reply_id}...")
        try:
            response_result = await self.reply_bot.process_reply(
                message=reply.message,
                post_context=post.content[:200] if post else ""
            )
        except Exception as e:
            logger.error(f"💬 process_reply failed: {e!s}")
            raise
        logger.info(f"💬 process_reply returned: keys={list(response_result.keys()) if response_result else None}")
        
        suggested = response_result.get("suggested_response")
        if not suggested or not str(suggested).strip():
            logger.warning(f"💬 ⚠️ AI did not return a suggested response for reply {reply_id}; result={response_result}")
            raise ValueError(
                "ה-AI לא החזיר תשובה. בדוק שמפתח API (OpenAI או Anthropic) מוגדר ב-.env ונסה שוב."
            )
        
        reply.suggested_response = suggested
        reply.suggested_channel = response_result.get("suggested_channel", "comment")
        reply.status = "ai_suggested"
        
        await self.session.flush()
        
        logger.info(f"💬 ✅ Response suggested for reply {reply_id}")
        return reply
    
    async def approve_and_send_response(
        self,
        reply_id: int,
        response_text: str = None,
        channel: str = None
    ) -> FacebookReply:
        """אישור ושליחת תשובה"""
        result = await self.session.execute(
            select(FacebookReply).where(FacebookReply.id == reply_id)
        )
        reply = result.scalar_one_or_none()
        
        if not reply:
            raise ValueError(f"Reply {reply_id} not found")
        
        # שימוש בתשובה המוצעת אם לא סופקה
        final_response = response_text or reply.suggested_response
        final_channel = channel or reply.suggested_channel or "comment"
        
        if not final_response:
            raise ValueError("No response text provided")
        
        # שליחת התשובה
        send_success = False
        send_error = None
        
        if final_channel == "messenger":
            # שליחה למסנג'ר
            if reply.fb_user_profile_url:
                result = await self.apify.send_single_message(
                    profile_url=reply.fb_user_profile_url,
                    message=final_response
                )
                if result:
                    send_success = True
                else:
                    send_error = "Messenger send failed"
                    logger.warning(f"💬 ⚠️ Messenger send may have failed for reply {reply_id}")
            else:
                send_error = "No profile URL for messenger"
        else:
            # שליחת תגובה בפייסבוק -- העברה לתוסף Chrome (בטוח, דפדפן אמיתי)
            reply.actual_response = final_response
            reply.response_channel = "comment"
            reply.status = "pending_extension"
            await self.session.flush()
            logger.info(f"💬 🔌 Reply {reply_id} queued for Chrome Extension")
            send_success = True
        
        if not send_success:
            # שמירת התשובה כמאושרת - ממתינה לפרסום ידני
            reply.actual_response = final_response
            reply.response_channel = final_channel
            reply.status = "approved_not_sent"
            
            await self.session.flush()
            
            logger.info(f"💬 ℹ️ Reply {reply_id} approved - awaiting manual posting ({send_error})")
            return reply, send_error
        
        # עדכון - רק אם השליחה הצליחה
        reply.actual_response = final_response
        reply.response_channel = final_channel
        reply.status = "responded"
        reply.responded_at = datetime.utcnow()
        
        await self.session.flush()
        
        logger.info(f"💬 ✅ Response sent for reply {reply_id} via {final_channel}")
        return reply, None
    
    # ========== Statistics ==========
    
    async def get_stats(self) -> Dict[str, Any]:
        """קבלת סטטיסטיקות"""
        # ספירת קבוצות
        groups_count = await self.session.execute(
            select(func.count(FacebookGroup.id)).where(FacebookGroup.is_active == True)
        )
        
        # ספירת קמפיינים
        campaigns_count = await self.session.execute(
            select(func.count(FacebookCampaign.id))
        )
        
        # ספירת פוסטים
        posts_stats = await self.session.execute(
            select(
                FacebookPost.status,
                func.count(FacebookPost.id)
            ).group_by(FacebookPost.status)
        )
        
        # ספירת תגובות
        replies_count = await self.session.execute(
            select(func.count(FacebookReply.id))
        )
        
        pending_replies = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                FacebookReply.status.in_(["new", "pending_response", "ai_suggested"])
            )
        )
        
        return {
            "groups": groups_count.scalar() or 0,
            "campaigns": campaigns_count.scalar() or 0,
            "posts": {row[0]: row[1] for row in posts_stats.all()},
            "replies": {
                "total": replies_count.scalar() or 0,
                "pending": pending_replies.scalar() or 0
            }
        }


# Factory function
def get_facebook_marketing_service(session: AsyncSession) -> FacebookMarketingService:
    """קבלת instance של Facebook Marketing Service"""
    return FacebookMarketingService(session)
