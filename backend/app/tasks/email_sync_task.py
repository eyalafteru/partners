"""
PartnerCalc OS - Email Sync Task
סנכרון מיילים בזמן אמת עם IMAP IDLE
"""
import imaplib
import asyncio
from datetime import datetime
from typing import Optional
from loguru import logger

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.imap_service import IMAPService


class EmailSyncTask:
    """
    משימת סנכרון מיילים בזמן אמת
    משתמש ב-IMAP IDLE לקבלת התראות מיידיות
    """
    
    def __init__(self):
        self.running = False
        self.imap_service = IMAPService()
        self.last_uid = None
        self.check_interval = 30  # בדיקה כל 30 שניות אם IDLE לא נתמך
    
    async def start(self):
        """התחלת הסנכרון"""
        self.running = True
        logger.info("📬 Email Sync Task started - listening for new emails...")
        
        while self.running:
            try:
                await self._check_new_emails()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"📬 Email sync error: {e}")
                await asyncio.sleep(60)  # המתנה דקה אם יש שגיאה
    
    async def stop(self):
        """עצירת הסנכרון"""
        self.running = False
        logger.info("📬 Email Sync Task stopped")
    
    async def _check_new_emails(self):
        """בדיקת מיילים חדשים"""
        try:
            # שליפת מיילים לא נקראו
            emails = await self.imap_service.fetch_unread_emails_async(limit=20)
            
            if not emails:
                return
            
            logger.info(f"📬 Found {len(emails)} unread emails")
            
            # עיבוד כל מייל
            for email_data in emails:
                await self._process_incoming_email(email_data)
        
        except Exception as e:
            logger.error(f"📬 Failed to check emails: {e}")
    
    async def _process_incoming_email(self, email_data: dict):
        """עיבוד מייל נכנס עם התאמת תרחישים"""
        from sqlalchemy import select
        from app.models.lead import Lead
        from app.models.communication import Communication
        from app.models.auto_reply import AutoReply, PendingReply
        from app.services.scenario_matcher import match_and_prepare_reply
        from app.services.smtp_service import get_smtp_service
        
        from_email = email_data.get("from_email", "")
        subject = email_data.get("subject", "")
        message_id = email_data.get("message_id", "")
        body = email_data.get("text_body", "")
        
        logger.info(f"📬 Processing email from {from_email}: {subject}")
        
        async with AsyncSessionLocal() as session:
            try:
                # בדיקה אם המייל כבר קיים במערכת
                if message_id:
                    existing = await session.execute(
                        select(Communication).where(
                            Communication.external_id == message_id
                        )
                    )
                    if existing.scalar_one_or_none():
                        logger.debug(f"📬 Email already exists: {message_id}")
                        return
                
                # חיפוש ליד לפי כתובת המייל
                lead = None
                if from_email:
                    # חיפוש בכל הלידים
                    lead_result = await session.execute(
                        select(Lead).where(Lead.contact_info.isnot(None)).limit(500)
                    )
                    leads = lead_result.scalars().all()
                    
                    for l in leads:
                        contact = l.contact_info or {}
                        if (contact.get("whois_email") == from_email or 
                            from_email in (contact.get("emails") or [])):
                            lead = l
                            break
                
                if lead:
                    # שמירת המייל כתקשורת נכנסת
                    communication = Communication(
                        lead_id=lead.id,
                        channel="email",
                        direction="inbound",
                        subject=subject,
                        message_body=body,
                        status="delivered",
                        external_id=message_id,
                        sent_at=email_data.get("received_at") or datetime.utcnow()
                    )
                    
                    session.add(communication)
                    
                    # עדכון סטטוס הליד
                    if lead.status == "contacted":
                        lead.status = "responded"
                        logger.info(f"📬 Lead {lead.id} status updated to 'responded'")
                    
                    await session.commit()
                    logger.info(f"📬 ✅ Email saved for lead {lead.id}: {subject}")
                    
                    # ========== WHATSAPP NOTIFICATION ==========
                    await self._send_whatsapp_alert(from_email, subject, lead.domain)
                    
                    # ========== AUTO-REPLY LOGIC ==========
                    await self._handle_auto_reply(
                        session, lead, from_email, subject, body,
                        communication_id=communication.id
                    )
                else:
                    logger.info(f"📬 No matching lead found for {from_email}")
            
            except Exception as e:
                logger.error(f"📬 Failed to process email: {e}")
                await session.rollback()
    
    async def _handle_auto_reply(
        self,
        session,
        lead,
        from_email: str,
        email_subject: str,
        email_body: str,
        communication_id: int = None
    ):
        """
        טיפול בתשובה אוטומטית - תמיד דורש אישור אנושי!
        כל תגובת AI נשמרת לאישור במסך האימיילים
        """
        from sqlalchemy import select
        from app.models.auto_reply import AutoReply, PendingReply
        from app.services.scenario_matcher import match_and_prepare_reply
        
        try:
            # בדיקת הגדרות auto-reply
            settings_result = await session.execute(select(AutoReply))
            auto_reply_settings = settings_result.scalar_one_or_none()
            
            if not auto_reply_settings or not auto_reply_settings.email_enabled:
                logger.debug("📬 Auto-reply disabled")
                return
            
            # חילוץ שם הליד
            contact = lead.contact_info or {}
            lead_name = contact.get("name") or contact.get("whois_name") or "שלום"
            
            # התאמת תרחיש
            from app.database import SessionLocal
            with SessionLocal() as sync_session:
                reply_data = await match_and_prepare_reply(
                    db=sync_session,
                    email_subject=email_subject,
                    email_body=email_body,
                    lead_name=lead_name,
                    lead_domain=lead.domain
                )
            
            if not reply_data.get("matched"):
                logger.info("📬 No matching scenario found for auto-reply")
                return
            
            logger.info(
                f"📬 Matched scenario: {reply_data['scenario_name']} "
                f"({reply_data['method']}, confidence: {reply_data['confidence']:.2f})"
            )
            
            # יצירת נושא לתשובה
            response_subject = reply_data.get("response_subject", "")
            if not response_subject:
                response_subject = f"Re: {email_subject}" if email_subject else "תגובה"
            
            # בניית הסבר לבודק האנושי
            reasoning_parts = [
                f"תרחיש: {reply_data.get('scenario_display_name', reply_data['scenario_name'])}",
                f"קטגוריה: {reply_data['scenario_category']}",
                f"שיטת זיהוי: {reply_data['method']}",
                f"ביטחון: {reply_data['confidence']:.0%}",
            ]
            if reply_data.get("requires_human"):
                reasoning_parts.append("⚠️ התרחיש מסומן כדורש טיפול אנושי")
            
            ai_reasoning = " | ".join(reasoning_parts)
            
            # 🚨 תמיד שומרים לאישור אנושי - אף פעם לא שולחים אוטומטית!
            pending = PendingReply(
                communication_id=communication_id,
                lead_id=lead.id,
                scenario_name=reply_data["scenario_name"],
                scenario_category=reply_data["scenario_category"],
                match_confidence=f"{reply_data['confidence']:.0%}",
                match_method=reply_data["method"],
                suggested_subject=response_subject,
                suggested_reply=reply_data["response_body"],
                ai_reasoning=ai_reasoning,
                trigger_message=email_body[:1000],
                trigger_subject=email_subject,
                sender_email=from_email,
                status="pending"
            )
            session.add(pending)
            await session.commit()
            
            logger.info(
                f"📬 ✅ Reply queued for human approval "
                f"(lead {lead.id}, scenario: {reply_data['scenario_name']})"
            )
        
        except Exception as e:
            logger.error(f"📬 Auto-reply error: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    async def _send_whatsapp_alert(self, from_email: str, subject: str, lead_domain: str = None):
        """שליחת התראת WhatsApp על מייל חדש"""
        try:
            from app.services.whatsapp_service import get_whatsapp_service
            
            whatsapp = get_whatsapp_service()
            if whatsapp.is_configured:
                await whatsapp.send_new_email_alert(from_email, subject, lead_domain)
        except Exception as e:
            logger.error(f"📱 Failed to send WhatsApp alert: {e}")


# Singleton instance
_email_sync_task: Optional[EmailSyncTask] = None


def get_email_sync_task() -> EmailSyncTask:
    """קבלת instance של Email Sync Task"""
    global _email_sync_task
    if _email_sync_task is None:
        _email_sync_task = EmailSyncTask()
    return _email_sync_task


async def start_email_sync():
    """התחלת סנכרון מיילים - נקרא מ-lifespan"""
    # בדיקה אם יש הגדרות IMAP
    if not settings.imap_password:
        logger.warning("📬 IMAP password not set - email sync disabled")
        return
    
    task = get_email_sync_task()
    await task.start()


async def stop_email_sync():
    """עצירת סנכרון מיילים"""
    task = get_email_sync_task()
    await task.stop()
