"""
PartnerCalc OS - AI Reply Service
שירות מענה אוטומטי באמצעות GPT
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.config import settings
from app.models.communication import Communication
from app.models.lead import Lead
from app.models.auto_reply import AutoReply, PendingReply
from app.models.calculator import Calculator
from app.services.smtp_service import get_smtp_service


AI_REPLY_PROMPT = """You are an email assistant for a financial calculator company.

Context:
- Company: הלוואות ישראל
- Product: Financial calculators (loans, mortgages, savings)
- Lead's website: {domain}
- Lead's name: {contact_name}
- Recommended calculator: {calculator_name}

Previous conversation:
{conversation_history}

Customer's latest message:
{customer_message}

Instructions:
1. Write a professional, friendly reply in Hebrew
2. Keep it concise (2-3 paragraphs max)
3. If they ask about pricing, mention standard rates (199 ש"ח לחודש עם 14 ימי ניסיון חינם)
4. If they're interested, suggest scheduling a demo call
5. If they want to unsubscribe, be polite and confirm
6. Don't make promises you can't keep
7. Be helpful and solution-oriented

Reply:"""


class AIReplyService:
    """
    שירות יצירת תשובות אוטומטיות ע"י AI
    """
    
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
    
    async def generate_reply(
        self,
        message: Communication,
        lead: Lead,
        conversation_history: List[Communication] = None,
        session: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        יצירת תשובה אוטומטית להודעה נכנסת
        
        Returns:
            {
                "success": True/False,
                "reply": "תשובה מוצעת...",
                "reasoning": "למה הוצע...",
                "should_escalate": False
            }
        """
        try:
            # Get calculator info if available
            calculator_name = "מחשבון פיננסי"
            if lead.recommended_calc_id:
                result = await session.execute(
                    select(Calculator).where(Calculator.id == lead.recommended_calc_id)
                )
                calculator = result.scalar_one_or_none()
                if calculator:
                    calculator_name = calculator.name
            
            # Get contact info
            contact_name = ""
            if lead.contact_info:
                contact_name = lead.contact_info.get("whois_name", "")
            
            # Build conversation history
            history_text = ""
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages
                    direction = "לקוח" if msg.direction == "inbound" else "אנחנו"
                    history_text += f"{direction}: {msg.message_body}\n\n"
            
            # Prepare prompt
            prompt = AI_REPLY_PROMPT.format(
                domain=lead.domain or "",
                contact_name=contact_name or "לקוח יקר",
                calculator_name=calculator_name,
                conversation_history=history_text or "אין היסטוריה קודמת",
                customer_message=message.message_body
            )
            
            # Call OpenAI
            reply_text = await self._call_gpt(prompt)
            
            if not reply_text:
                return {
                    "success": False,
                    "error": "Failed to generate reply"
                }
            
            return {
                "success": True,
                "reply": reply_text,
                "reasoning": f"תשובה נוצרה עבור הודעה מ-{lead.domain}",
                "should_escalate": False
            }
            
        except Exception as e:
            logger.error(f"AI reply generation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _call_gpt(self, prompt: str) -> Optional[str]:
        """
        קריאה ל-OpenAI GPT
        """
        import httpx
        
        if not self.openai_api_key:
            logger.error("OpenAI API key not configured")
            return None
        
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a helpful business assistant. Always respond in Hebrew."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"GPT API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"GPT call error: {e}")
            return None
    
    def check_keywords_for_escalation(self, message_body: str, keywords: List[str]) -> bool:
        """
        בדיקה אם ההודעה מכילה מילים שדורשות טיפול אנושי
        """
        message_lower = message_body.lower()
        
        for keyword in keywords:
            if keyword.lower() in message_lower:
                return True
        
        return False
    
    def is_within_business_hours(
        self, 
        start_time: str = "09:00", 
        end_time: str = "18:00"
    ) -> bool:
        """
        בדיקה אם אנחנו בשעות פעילות
        """
        now = datetime.now()
        
        # Parse times
        start_hour, start_min = map(int, start_time.split(":"))
        end_hour, end_min = map(int, end_time.split(":"))
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        # Check if weekend (Friday afternoon to Saturday night in Israel)
        if now.weekday() == 4 and current_minutes > 14 * 60:  # Friday after 14:00
            return False
        if now.weekday() == 5:  # Saturday
            return False
        
        return start_minutes <= current_minutes <= end_minutes


async def handle_incoming_email(
    communication: Communication,
    session: AsyncSession
):
    """
    טיפול בהודעת מייל נכנסת - הפונקציה הראשית
    
    Called from webhooks.py after saving inbound email
    """
    logger.info(f"Handling incoming email: {communication.id}")
    
    # Get auto-reply settings
    result = await session.execute(select(AutoReply).limit(1))
    settings_obj = result.scalar_one_or_none()
    
    if not settings_obj:
        logger.info("No auto-reply settings found - skipping")
        return
    
    if not settings_obj.email_enabled:
        logger.info("Email auto-reply is disabled")
        return
    
    if settings_obj.email_mode == "off":
        logger.info("Email mode is OFF - skipping auto-reply")
        return
    
    # Get lead
    result = await session.execute(
        select(Lead).where(Lead.id == communication.lead_id)
    )
    lead = result.scalar_one_or_none()
    
    if not lead:
        logger.warning(f"Lead not found for communication {communication.id}")
        return
    
    # Check for escalation keywords
    ai_service = AIReplyService()
    keywords = settings_obj.keywords_trigger_human or ["ביטול", "תלונה", "החזר", "מנהל"]
    
    if ai_service.check_keywords_for_escalation(communication.message_body, keywords):
        logger.info(f"Message contains escalation keyword - requires human attention")
        # Could send notification to admin here
        return
    
    # Check business hours
    if settings_obj.business_hours_only:
        if not ai_service.is_within_business_hours(
            settings_obj.business_hours_start,
            settings_obj.business_hours_end
        ):
            logger.info("Outside business hours - will handle later")
            # Could queue for later here
            return
    
    # Check max auto-replies
    result = await session.execute(
        select(func.count(Communication.id))
        .where(
            Communication.lead_id == lead.id,
            Communication.is_auto_reply == True,
            Communication.channel == "email"
        )
    )
    auto_reply_count = result.scalar()
    
    if auto_reply_count >= settings_obj.max_auto_replies_per_lead:
        logger.info(f"Max auto-replies ({settings_obj.max_auto_replies_per_lead}) reached for lead {lead.id}")
        return
    
    # Get conversation history
    result = await session.execute(
        select(Communication)
        .where(
            Communication.lead_id == lead.id,
            Communication.channel == "email"
        )
        .order_by(Communication.sent_at.asc())
    )
    history = result.scalars().all()
    
    # Generate AI reply
    reply_result = await ai_service.generate_reply(
        message=communication,
        lead=lead,
        conversation_history=history,
        session=session
    )
    
    if not reply_result.get("success"):
        logger.error(f"Failed to generate AI reply: {reply_result.get('error')}")
        return
    
    suggested_reply = reply_result["reply"]
    
    if settings_obj.email_mode == "suggest":
        # Save as pending for approval
        pending = PendingReply(
            communication_id=communication.id,
            suggested_reply=suggested_reply,
            ai_reasoning=reply_result.get("reasoning"),
            status="pending"
        )
        session.add(pending)
        await session.commit()
        
        logger.info(f"AI reply saved as pending for approval: {pending.id}")
        # TODO: Send notification to admin
        
    elif settings_obj.email_mode == "auto":
        # Send immediately (with optional delay)
        import asyncio
        
        delay = settings_obj.email_delay_seconds or 0
        if delay > 0:
            logger.info(f"Waiting {delay} seconds before auto-send...")
            await asyncio.sleep(delay)
        
        # Get recipient email
        to_email = None
        if lead.contact_info:
            to_email = lead.contact_info.get("whois_email")
            if not to_email:
                emails = lead.contact_info.get("emails", [])
                if emails:
                    to_email = emails[0]
        
        if not to_email:
            logger.warning(f"No email address for lead {lead.id} - cannot auto-reply")
            return
        
        # Create reply subject
        subject = communication.subject or ""
        if not subject.startswith("Re:"):
            subject = f"Re: {subject}"
        
        # Create communication record
        reply_comm = Communication(
            lead_id=lead.id,
            channel="email",
            direction="outbound",
            message_body=suggested_reply,
            subject=subject,
            status="pending",
            is_auto_reply=True,
            thread_id=communication.thread_id or str(communication.id),
            in_reply_to_id=communication.id
        )
        session.add(reply_comm)
        await session.flush()
        
        # Send via SMTP
        smtp_service = get_smtp_service()
        send_result = await smtp_service.send_email_async(
            to_email=to_email,
            subject=subject,
            body=suggested_reply
        )
        
        if send_result.get("success"):
            reply_comm.status = "sent"
            reply_comm.external_id = send_result.get("message_id")
            logger.info(f"Auto-reply sent successfully: {reply_comm.id}")
        else:
            reply_comm.status = "failed"
            reply_comm.error_message = send_result.get("error")
            logger.error(f"Auto-reply send failed: {send_result.get('error')}")
        
        await session.commit()


# Singleton
_ai_reply_service: Optional[AIReplyService] = None


def get_ai_reply_service() -> AIReplyService:
    """קבלת instance של AI Reply Service"""
    global _ai_reply_service
    if _ai_reply_service is None:
        _ai_reply_service = AIReplyService()
    return _ai_reply_service
