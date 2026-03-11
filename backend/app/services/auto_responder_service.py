"""
PartnerCalc OS - Auto Responder Service
שירות לתגובות אוטומטיות - תגובה ראשונה + תשובות למגיבים
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from loguru import logger

from app.models.facebook_marketing import FacebookPost, FacebookCampaign, FacebookReply
from app.models.calculator import Calculator
from app.models.post_strategy import PostStrategy


class AutoResponderService:
    """שירות לתגובות אוטומטיות"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_posts_needing_first_comment(self) -> List[FacebookPost]:
        """
        שליפת פוסטים שצריכים תגובה ראשונה
        - פורסמו בהצלחה
        - יש תוכן לתגובה ראשונה
        - עדיין לא נשלחה תגובה ראשונה
        """
        result = await self.session.execute(
            select(FacebookPost).where(
                and_(
                    FacebookPost.status == "published",
                    FacebookPost.first_comment_content.isnot(None),
                    FacebookPost.first_comment_posted == False
                )
            )
        )
        return result.scalars().all()
    
    async def get_post(self, post_id: int) -> Optional[FacebookPost]:
        """שליפת פוסט לפי ID"""
        result = await self.session.execute(
            select(FacebookPost).where(FacebookPost.id == post_id)
        )
        return result.scalar_one_or_none()
    
    async def get_campaign(self, campaign_id: int) -> Optional[FacebookCampaign]:
        """שליפת קמפיין לפי ID"""
        result = await self.session.execute(
            select(FacebookCampaign).where(FacebookCampaign.id == campaign_id)
        )
        return result.scalar_one_or_none()
    
    async def post_first_comment(self, post_id: int) -> bool:
        """
        פרסום תגובה ראשונה לפוסט
        """
        post = await self.get_post(post_id)
        if not post or not post.first_comment_content:
            logger.warning(f"Post {post_id} not found or has no first comment content")
            return False
        
        if post.first_comment_posted:
            logger.info(f"First comment already posted for post {post_id}")
            return True
        
        if not post.fb_post_url:
            logger.warning(f"Post {post_id} has no Facebook URL")
            return False
        
        try:
            # Import Apify service for posting comments
            from app.services.apify_service import get_apify_service
            
            apify = get_apify_service()
            
            # Use reply_to_comment which handles actor ID and cookies
            result = await apify.reply_to_comment(
                post_url=post.fb_post_url,
                reply_message=post.first_comment_content
            )
            
            if result and result.get("success"):
                post.first_comment_posted = True
                logger.info(f"✅ First comment posted for post {post_id}")
                return True
            else:
                error = result.get("error", "Unknown") if result else "No result"
                logger.error(f"❌ Failed to post first comment for post {post_id}: {error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error posting first comment for post {post_id}: {e}")
            return False
    
    async def check_and_respond_to_comments(self, campaign_id: int) -> int:
        """
        בדיקה ותשובה אוטומטית לתגובות בקמפיין.
        עובד רק על תגובות עם סטטוס "ai_suggested" (כבר יש הצעת AI מוכנה).
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign or not campaign.auto_responder_enabled:
            return 0
        
        # בדיקת מגבלה יומית
        today_count = await self._get_today_auto_replies_count(campaign_id)
        daily_limit = campaign.auto_responder_daily_limit or 10
        if today_count >= daily_limit:
            logger.info(f"Daily limit ({daily_limit}) reached for campaign {campaign_id}: {today_count} sent today")
            return 0
        
        # שליפת תגובות שמוכנות לתשובה אוטומטית
        replies = await self._get_pending_replies(campaign_id)
        
        responses_sent = 0
        for reply in replies:
            if today_count + responses_sent >= daily_limit:
                logger.info(f"Daily limit reached mid-batch for campaign {campaign_id}")
                break
            
            if await self.should_respond(reply, campaign):
                success = await self.send_auto_response(reply, campaign)
                if success:
                    responses_sent += 1
        
        return responses_sent
    
    async def should_respond(self, reply: FacebookReply, campaign: FacebookCampaign) -> bool:
        """
        לוגיקת החלטה האם להגיב אוטומטית.
        """
        # אל תגיב לספאם
        if reply.ai_detected_intent == "spam":
            return False
        
        # אל תגיב אם כבר נענה או נדחה
        if reply.status in ["responded", "ignored", "approved"]:
            return False
        
        # חייב להיות הצעת AI מוכנה
        if not reply.suggested_response:
            return False
        
        # בדיקה אם AI ממליץ להעביר לטיפול אנושי
        from app.services.facebook_reply_service import get_facebook_reply_service
        reply_bot = get_facebook_reply_service()
        if reply_bot.should_escalate_to_human(reply.ai_analysis or {}):
            logger.info(f"Reply {reply.id} escalated to human (intent: {reply.ai_detected_intent})")
            return False
        
        # בדיקת עיכוב - המתנה לפחות X דקות מרגע קבלת התגובה
        delay_minutes = campaign.auto_responder_delay_minutes or 5
        if reply.received_at:
            delay = timedelta(minutes=delay_minutes)
            time_since = datetime.now() - reply.received_at.replace(tzinfo=None)
            if time_since < delay:
                return False
        
        return True
    
    async def send_auto_response(self, reply: FacebookReply, campaign: FacebookCampaign) -> bool:
        """
        שליחת תשובה אוטומטית.
        משתמש בהצעת AI הקיימת (suggested_response), או מייצר חדשה אם אין.
        """
        try:
            # שימוש בהצעה קיימת, או יצירה חדשה כ-fallback
            response_text = reply.suggested_response
            if not response_text:
                response_text = await self._generate_response(reply, campaign)
            if not response_text:
                logger.warning(f"No response text available for reply {reply.id}")
                return False
            
            # בחירת ערוץ לשליחה
            channel = campaign.auto_responder_type or "comment"
            if channel == "ai_decide":
                channel = reply.suggested_channel or ("messenger" if reply.wants_private else "comment")
            
            # שליחה בהתאם לערוץ
            if channel == "messenger":
                success = await self._send_messenger_reply(reply, response_text)
            else:
                success = await self._send_comment_reply(reply, response_text)
            
            if success:
                reply.status = "responded"
                reply.actual_response = response_text
                reply.response_channel = channel
                reply.responded_at = datetime.now()
                
                # עדכון מונה בפוסט
                post = await self.get_post(reply.post_id)
                if post:
                    post.auto_replies_sent = (post.auto_replies_sent or 0) + 1
                
                logger.info(f"✅ Auto response sent to reply {reply.id} via {channel}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error sending auto response for reply {reply.id}: {e}")
            return False
    
    async def _generate_response(self, reply: FacebookReply, campaign: FacebookCampaign) -> Optional[str]:
        """
        יצירת תשובה - משתמש בתבנית או ב-AI
        """
        # אם יש תבנית - השתמש בה
        if campaign.auto_responder_template:
            # החלפת משתנים בסיסיים
            template = campaign.auto_responder_template
            template = template.replace("{user_name}", reply.fb_user_name or "")
            return template
        
        # אחרת - יצירת תשובה עם AI
        try:
            from app.services.post_generator_service import get_post_generator_service
            
            generator = get_post_generator_service()
            
            # קבלת מידע על המחשבון אם יש
            calculator_info = ""
            if campaign.calculator_id:
                result = await self.session.execute(
                    select(Calculator).where(Calculator.id == campaign.calculator_id)
                )
                calc = result.scalar_one_or_none()
                if calc:
                    calculator_info = f"המחשבון שלנו: {calc.name} - {calc.target_url}"
            
            prompt = f"""
            תגובה שהתקבלה: {reply.message}
            שם המגיב: {reply.fb_user_name}
            {calculator_info}
            
            כתוב תשובה קצרה, ידידותית ומועילה בשפה ניטרלית מבחינת מגדר (מתאימה לנשים ולגברים).
            השתמש בצורות כמו "ניתן לבדוק", "אפשר לראות", "מוזמנים לנסות" במקום צורות מגדריות.
            """
            
            response = await generator.generate_text(
                prompt=prompt,
                max_tokens=150
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return None
    
    async def _send_comment_reply(self, reply: FacebookReply, text: str) -> bool:
        """שליחת תשובה כתגובה"""
        try:
            from app.services.apify_service import get_apify_service
            
            apify = get_apify_service()
            
            # Get post URL (async query - do not use reply.post lazy load in async context)
            post = await self.get_post(reply.post_id) if reply.post_id else None
            post_url = post.fb_post_url if post else None
            
            if not post_url:
                logger.error(f"No post URL found for reply {reply.id}")
                return False
            
            result = await apify.reply_to_comment(
                post_url=post_url,
                reply_message=text,
                comment_id=reply.fb_comment_id
            )
            
            return result and result.get("success", False)
            
        except Exception as e:
            logger.error(f"Error sending comment reply: {e}")
            return False
    
    async def _send_messenger_reply(self, reply: FacebookReply, text: str) -> bool:
        """שליחת תשובה במסנג'ר"""
        try:
            from app.services.apify_service import get_apify_service
            
            apify = get_apify_service()
            
            result = await apify.send_single_message(
                profile_url=reply.fb_user_id,
                message=text
            )
            
            return result is not None
            
        except Exception as e:
            logger.error(f"Error sending messenger reply: {e}")
            return False
    
    async def _get_today_auto_replies_count(self, campaign_id: int) -> int:
        """ספירת תשובות אוטומטיות להיום"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.session.execute(
            select(func.count(FacebookReply.id)).where(
                and_(
                    FacebookReply.responded_at >= today,
                    FacebookReply.response_channel.isnot(None),
                    # הצטרף לפוסטים של הקמפיין
                    FacebookReply.post_id.in_(
                        select(FacebookPost.id).where(FacebookPost.campaign_id == campaign_id)
                    )
                )
            )
        )
        return result.scalar_one() or 0
    
    async def _get_pending_replies(self, campaign_id: int) -> List[FacebookReply]:
        """שליפת תגובות עם הצעת AI מוכנה שמחכות לתשובה אוטומטית"""
        result = await self.session.execute(
            select(FacebookReply).where(
                and_(
                    FacebookReply.status.in_(["ai_suggested", "new"]),
                    FacebookReply.post_id.in_(
                        select(FacebookPost.id).where(
                            and_(
                                FacebookPost.campaign_id == campaign_id,
                                FacebookPost.status == "published"
                            )
                        )
                    )
                )
            ).order_by(FacebookReply.received_at)
        )
        return result.scalars().all()


def get_auto_responder_service(session: AsyncSession) -> AutoResponderService:
    """Factory function"""
    return AutoResponderService(session)
