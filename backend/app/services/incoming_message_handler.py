"""
PartnerCalc OS - Incoming Message Handler
Interface משותף לטיפול בהודעות/תגובות נכנסות מכל הערוצים.

כל ערוץ (Facebook, Email, WhatsApp, SMS) מממש את אותו flow:
  1. receive   - קליטת ההודעה ושמירה ב-DB
  2. analyze   - ניתוח AI (intent, interest, sentiment)
  3. suggest   - יצירת הצעת תגובה
  4. approve   - אישור/עריכה/דחייה ידנית (או אוטומטי)
  5. send      - שליחת התגובה דרך הערוץ המתאים
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class IncomingMessageHandler(ABC):
    """
    Base class לטיפול בהודעות נכנסות.
    כל ערוץ (Facebook, Email, WhatsApp) יורש ומממש את המתודות.
    """
    
    @property
    @abstractmethod
    def channel_name(self) -> str:
        """שם הערוץ: facebook, email, whatsapp, sms"""
        ...
    
    @abstractmethod
    async def receive(self, raw_data: Dict[str, Any]) -> Optional[int]:
        """
        קליטת הודעה נכנסת ושמירה ב-DB.
        
        Args:
            raw_data: המידע הגולמי מהערוץ (webhook payload, scraped data, etc.)
            
        Returns:
            message_id - מזהה ההודעה שנשמרה, או None אם נכשל
        """
        ...
    
    @abstractmethod
    async def analyze(self, message_id: int) -> Dict[str, Any]:
        """
        ניתוח AI של ההודעה.
        
        Returns:
            dict עם intent, interest_level, sentiment, wants_private, etc.
        """
        ...
    
    @abstractmethod
    async def suggest(self, message_id: int) -> Optional[str]:
        """
        יצירת הצעת תגובה מבוססת AI.
        
        Returns:
            טקסט התגובה המוצעת, או None אם לא ניתן
        """
        ...
    
    @abstractmethod
    async def send(self, message_id: int, response_text: str, channel: str = None) -> bool:
        """
        שליחת תגובה דרך הערוץ.
        
        Returns:
            True אם נשלח בהצלחה
        """
        ...
    
    async def process_full(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        עיבוד מלא: receive -> analyze -> suggest.
        (לא שולח - ממתין לאישור ידני, אלא אם מוגדר auto)
        
        Returns:
            dict עם message_id, analysis, suggested_response
        """
        result = {
            "channel": self.channel_name,
            "message_id": None,
            "analysis": {},
            "suggested_response": None,
            "status": "failed"
        }
        
        try:
            # 1. קליטה
            message_id = await self.receive(raw_data)
            if not message_id:
                result["status"] = "receive_failed"
                return result
            result["message_id"] = message_id
            
            # 2. ניתוח
            analysis = await self.analyze(message_id)
            result["analysis"] = analysis
            
            # 3. הצעה
            suggested = await self.suggest(message_id)
            result["suggested_response"] = suggested
            result["status"] = "ai_suggested" if suggested else "analyzed"
            
        except Exception as e:
            logger.error(f"[{self.channel_name}] process_full error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        
        return result


class FacebookIncomingHandler(IncomingMessageHandler):
    """
    Handler לתגובות נכנסות מפייסבוק.
    עוטף את הלוגיקה הקיימת ב-FacebookMarketingService.
    """
    
    @property
    def channel_name(self) -> str:
        return "facebook"
    
    async def receive(self, raw_data: Dict[str, Any]) -> Optional[int]:
        """Facebook comments are received via Apify polling in sync_post_comments"""
        raise NotImplementedError("Facebook uses polling via sync_post_comments, not direct receive")
    
    async def analyze(self, message_id: int) -> Dict[str, Any]:
        """ניתוח תגובת פייסבוק"""
        from app.services.facebook_reply_service import get_facebook_reply_service
        bot = get_facebook_reply_service()
        
        from app.database import get_async_session_context
        from app.models.facebook_marketing import FacebookReply
        from sqlalchemy import select
        
        async with get_async_session_context() as session:
            result = await session.execute(
                select(FacebookReply).where(FacebookReply.id == message_id)
            )
            reply = result.scalar_one_or_none()
            if not reply:
                return {}
            
            analysis = await bot.analyze_reply(reply.message or "")
            reply.ai_detected_intent = analysis.get("intent")
            reply.ai_analysis = analysis
            reply.wants_private = analysis.get("wants_private", False)
            await session.commit()
            
            return analysis
    
    async def suggest(self, message_id: int) -> Optional[str]:
        """יצירת הצעת תגובה לפייסבוק"""
        from app.database import get_async_session_context
        from app.services.facebook_marketing_service import get_facebook_marketing_service
        
        async with get_async_session_context() as session:
            service = get_facebook_marketing_service(session)
            reply = await service.generate_reply_response(message_id)
            await session.commit()
            return reply.suggested_response if reply else None
    
    async def send(self, message_id: int, response_text: str, channel: str = None) -> bool:
        """שליחת תגובה בפייסבוק"""
        from app.database import get_async_session_context
        from app.services.facebook_marketing_service import get_facebook_marketing_service
        
        async with get_async_session_context() as session:
            service = get_facebook_marketing_service(session)
            try:
                await service.approve_and_send_response(
                    reply_id=message_id,
                    response_text=response_text,
                    channel=channel
                )
                await session.commit()
                return True
            except Exception as e:
                logger.error(f"Facebook send error: {e}")
                return False
