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
from app.services.post_generator_service import get_post_generator_service
from app.services.apify_service import get_apify_service
from app.services.facebook_reply_service import get_facebook_reply_service


class FacebookMarketingService:
    """שירות מרכזי לניהול פרסום בקבוצות פייסבוק"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.post_generator = get_post_generator_service()
        self.apify = get_apify_service()
        self.reply_bot = get_facebook_reply_service()
    
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
        """יצירת פוסטים לקמפיין"""
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
        
        # יצירת פוסטים
        groups_data = [{"id": g.id, "name": g.name} for g in groups]
        
        generated = await self.post_generator.generate_campaign_posts(
            topic=campaign.topic,
            groups=groups_data,
            image_percentage=campaign.image_percentage,
            base_template=base_template,
            target_audience=campaign.target_audience or ""
        )
        
        # שמירת הפוסטים ב-DB
        posts = []
        for gen_post in generated:
            post = FacebookPost(
                campaign_id=campaign.id,
                group_id=gen_post["group_id"],
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
        """יצירת פוסט בודד לקבוצה בקמפיין"""
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
        
        # קבלת פוסטים קודמים לקבוצה זו (להימנע מחזרות)
        prev_posts_result = await self.session.execute(
            select(FacebookPost.content).where(
                FacebookPost.group_id == group_id,
                FacebookPost.campaign_id == campaign_id
            ).limit(5)
        )
        previous_posts = [p[0] for p in prev_posts_result.fetchall() if p[0]]
        
        # יצירת הפוסט
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
        
        # יצירת הפוסט ב-DB
        post = FacebookPost(
            campaign_id=campaign.id,
            group_id=group_id,
            content=content,
            has_image=has_image,
            image_prompt=image_prompt,
            image_url=image_url,
            status="pending_approval"
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
        
        if post.status != "approved":
            raise ValueError(f"Post {post_id} is not approved")
        
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
        
        # פרסום דרך Apify
        post.status = "publishing"
        await self.session.flush()
        
        run_info = await self.apify.post_single(
            group_url=group.url,
            message=post.content
        )
        
        if run_info:
            post.status = "published"
            post.apify_run_id = run_info.get("id")
            post.published_at = datetime.utcnow()
            
            # עדכון קבוצה
            group.total_posts += 1
            group.last_post_at = datetime.utcnow()
            
            # עדכון קמפיין
            if post.campaign_id:
                campaign = await self.get_campaign(post.campaign_id)
                if campaign:
                    campaign.total_posts_published += 1
            
            logger.info(f"📤 ✅ Post {post_id} published")
        else:
            post.status = "failed"
            post.publish_error = "Apify run failed"
            logger.error(f"📤 ❌ Post {post_id} publish failed")
        
        await self.session.flush()
        return post
    
    # ========== Replies Management ==========
    
    async def sync_post_comments(self, post_id: int) -> List[FacebookReply]:
        """סנכרון תגובות לפוסט"""
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
        
        new_replies = []
        
        for comment in comments:
            fb_comment_id = comment.get("id") or comment.get("commentId")
            if not fb_comment_id:
                continue
            
            # בדיקה אם כבר קיים
            existing = await self.session.execute(
                select(FacebookReply).where(
                    FacebookReply.fb_comment_id == fb_comment_id
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # ניתוח התגובה
            message = comment.get("text", "")
            analysis = await self.reply_bot.analyze_reply(
                message=message,
                post_context=post.content[:200]
            )
            
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
                status="new",
                received_at=datetime.utcnow()
            )
            self.session.add(reply)
            new_replies.append(reply)
        
        # עדכון ספירה
        post.replies_count = (post.replies_count or 0) + len(new_replies)
        
        await self.session.flush()
        
        logger.info(f"💬 ✅ Synced {len(new_replies)} new replies for post {post_id}")
        return new_replies
    
    async def get_pending_replies(self) -> List[FacebookReply]:
        """קבלת תגובות ממתינות לטיפול"""
        result = await self.session.execute(
            select(FacebookReply).where(
                FacebookReply.status.in_(["new", "pending_response"])
            ).order_by(FacebookReply.created_at.desc())
        )
        return result.scalars().all()
    
    async def generate_reply_response(self, reply_id: int) -> FacebookReply:
        """יצירת תשובה מוצעת לתגובה"""
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
        response_result = await self.reply_bot.process_reply(
            message=reply.message,
            post_context=post.content[:200] if post else ""
        )
        
        reply.suggested_response = response_result.get("suggested_response")
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
        if final_channel == "messenger":
            # שליחה למסנג'ר
            if reply.fb_user_profile_url:
                await self.apify.send_single_message(
                    profile_url=reply.fb_user_profile_url,
                    message=final_response
                )
        else:
            # TODO: שליחת תגובה בפייסבוק - דורש Actor מותאם
            logger.warning("Comment reply not yet implemented - needs custom Actor")
        
        # עדכון
        reply.actual_response = final_response
        reply.response_channel = final_channel
        reply.status = "responded"
        reply.responded_at = datetime.utcnow()
        
        await self.session.flush()
        
        logger.info(f"💬 ✅ Response sent for reply {reply_id} via {final_channel}")
        return reply
    
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
