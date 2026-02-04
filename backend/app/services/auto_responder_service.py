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
            
            # Use the existing facebook-comment-reply actor
            result = await apify.run_actor(
                actor_id="facebook-comment-reply",
                input={
                    "postUrl": post.fb_post_url,
                    "replyMessage": post.first_comment_content,
                    # cookies will be loaded from saved cookies
                }
            )
            
            if result and result.get("success"):
                post.first_comment_posted = True
                logger.info(f"✅ First comment posted for post {post_id}")
                return True
            else:
                logger.error(f"❌ Failed to post first comment for post {post_id}: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error posting first comment for post {post_id}: {e}")
            return False
    
    async def check_and_respond_to_comments(self, campaign_id: int) -> int:
        """
        בדיקה ותשובה לתגובות חדשות בקמפיין
        """
        campaign = await self.get_campaign(campaign_id)
        if not campaign or not campaign.auto_responder_enabled:
            return 0
        
        # בדיקת מגבלה יומית
        today_count = await self._get_today_auto_replies_count(campaign_id)
        if today_count >= campaign.auto_responder_daily_limit:
            logger.info(f"Daily limit reached for campaign {campaign_id}")
            return 0
        
        # שליפת תגובות שצריכות תשובה
        replies = await self._get_pending_replies(campaign_id)
        
        responses_sent = 0
        for reply in replies:
            if today_count + responses_sent >= campaign.auto_responder_daily_limit:
                break
            
            if await self.should_respond(reply, campaign):
                success = await self.send_auto_response(reply, campaign)
                if success:
                    responses_sent += 1
        
        return responses_sent
    
    async def should_respond(self, reply: FacebookReply, campaign: FacebookCampaign) -> bool:
        """
        לוגיקת החלטה האם להגיב
        """
        # אל תגיב לספאם
        if reply.ai_detected_intent == "spam":
            return False
        
        # אל תגיב אם כבר נענה
        if reply.status in ["responded", "ignored"]:
            return False
        
        # בדיקת עיכוב
        if reply.received_at:
            delay = timedelta(minutes=campaign.auto_responder_delay_minutes)
            if datetime.now() - reply.received_at < delay:
                return False
        
        return True
    
    async def send_auto_response(self, reply: FacebookReply, campaign: FacebookCampaign) -> bool:
        """
        שליחת תשובה אוטומטית
        """
        try:
            # יצירת תשובה
            response_text = await self._generate_response(reply, campaign)
            if not response_text:
                return False
            
            # שליחה בהתאם לערוץ
            if campaign.auto_responder_type == "comment":
                success = await self._send_comment_reply(reply, response_text)
            elif campaign.auto_responder_type == "messenger":
                success = await self._send_messenger_reply(reply, response_text)
            else:
                # ai_decide - בחירה אוטומטית
                if reply.wants_private:
                    success = await self._send_messenger_reply(reply, response_text)
                else:
                    success = await self._send_comment_reply(reply, response_text)
            
            if success:
                reply.status = "responded"
                reply.actual_response = response_text
                reply.response_channel = campaign.auto_responder_type
                reply.responded_at = datetime.now()
                
                # עדכון מונה בפוסט
                post = await self.get_post(reply.post_id)
                if post:
                    post.auto_replies_sent = (post.auto_replies_sent or 0) + 1
                
                logger.info(f"✅ Auto response sent to reply {reply.id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error sending auto response: {e}")
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
            
            כתוב תשובה קצרה, ידידותית ומועילה.
            אם הוא מתעניין - הזמן אותו לבדוק את המחשבון.
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
            
            # שימוש ב-Actor לתגובות
            result = await apify.run_actor(
                actor_id="facebook-comment-reply",
                input={
                    "commentId": reply.fb_comment_id,
                    "replyMessage": text,
                }
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
            
            # שימוש ב-Actor למסנג'ר
            result = await apify.run_actor(
                actor_id="facebook-message-sender",
                input={
                    "recipientId": reply.fb_user_id,
                    "message": text,
                }
            )
            
            return result and result.get("success", False)
            
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
        """שליפת תגובות שמחכות לתשובה"""
        result = await self.session.execute(
            select(FacebookReply).where(
                and_(
                    FacebookReply.status == "new",
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
