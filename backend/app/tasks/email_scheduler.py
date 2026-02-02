"""
PartnerCalc OS - Email Scheduler
שליחת מיילים מתוזמנת מתור המיילים
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_, update
from sqlalchemy.orm import selectinload

from app.database import get_async_session_context
from app.models import EmailQueue, Lead, Blacklist
from app.services.smtp_service import get_smtp_service


async def get_settings() -> dict:
    """קבלת הגדרות Outreach"""
    from sqlalchemy import text
    async with get_async_session_context() as session:
        result = await session.execute(text("SELECT key, value FROM outreach_settings"))
        rows = result.fetchall()
        settings = {}
        for key, value in rows:
            if key in ['daily_limit', 'start_hour', 'end_hour', 'interval_minutes']:
                settings[key] = int(value)
            elif key == 'enabled':
                settings[key] = value.lower() == 'true'
            else:
                settings[key] = value
        return settings


async def is_blacklisted(session, email: str, domain: str = None) -> bool:
    """בדיקה אם מייל/דומיין ברשימה שחורה"""
    from sqlalchemy import or_
    conditions = [Blacklist.email == email]
    if domain:
        conditions.append(Blacklist.domain == domain)
    
    result = await session.execute(
        select(Blacklist).where(or_(*conditions)).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def send_scheduled_emails():
    """
    שליחת מיילים מתוזמנים
    
    לוגיקה:
    1. בדיקה אם בשעות פעילות
    2. חישוב כמה מיילים לשלוח בכל הפעלה
    3. שליפת מיילים ממתינים
    4. בדיקת תנאים (לא ברשימה שחורה, ליד יכול לקבל מייל)
    5. שליחה
    6. עדכון סטטוסים
    """
    settings = await get_settings()
    
    if not settings.get('enabled', True):
        logger.debug("📧 Email scheduler disabled")
        return
    
    now = datetime.now()
    current_hour = now.hour
    
    start_hour = settings.get('start_hour', 8)
    end_hour = settings.get('end_hour', 20)
    
    # Check if within working hours
    if not (start_hour <= current_hour < end_hour):
        logger.debug(f"📧 Outside working hours ({start_hour}:00 - {end_hour}:00)")
        return
    
    # Calculate how many emails to send
    daily_limit = settings.get('daily_limit', 100)
    interval_minutes = settings.get('interval_minutes', 15)
    
    # Working hours = end_hour - start_hour (e.g., 12 hours)
    working_hours = end_hour - start_hour
    intervals_per_day = (working_hours * 60) // interval_minutes
    
    emails_per_run = max(1, daily_limit // intervals_per_day)
    
    logger.info(f"📧 Scheduler running: {emails_per_run} emails this interval")
    
    smtp = get_smtp_service()
    sent_count = 0
    failed_count = 0
    
    async with get_async_session_context() as session:
        # Get pending emails scheduled for now or earlier
        result = await session.execute(
            select(EmailQueue)
            .options(selectinload(EmailQueue.lead))
            .where(
                and_(
                    EmailQueue.status == "pending",
                    EmailQueue.scheduled_at <= now
                )
            )
            .order_by(EmailQueue.scheduled_at.asc())
            .limit(emails_per_run)
        )
        queue_items = result.scalars().all()
        
        if not queue_items:
            logger.debug("📧 No pending emails in queue")
            return
        
        for item in queue_items:
            lead = item.lead
            
            # Double-check lead can be contacted
            if lead:
                # Already contacted but no response - BLOCKED
                if lead.last_contacted_at and not lead.last_response_at:
                    logger.warning(f"📧 Lead {lead.domain} already contacted without response - skipping")
                    item.status = "cancelled"
                    item.error_message = "Lead already contacted without response"
                    continue
                
                # Check blacklist
                if await is_blacklisted(session, item.to_email, lead.domain if lead else None):
                    logger.warning(f"📧 Email {item.to_email} is blacklisted - skipping")
                    item.status = "cancelled"
                    item.error_message = "Email/domain blacklisted"
                    continue
            
            # Send email
            try:
                result = await smtp.send_email_async(
                    to_email=item.to_email,
                    subject=item.subject,
                    body=item.body,
                    enable_tracking=True
                )
                
                if result.get("success"):
                    item.status = "sent"
                    item.sent_at = datetime.now()
                    sent_count += 1
                    
                    # Update lead
                    if lead:
                        lead.status = "contacted"
                        lead.last_contacted_at = datetime.now()
                        lead.outreach_count = (lead.outreach_count or 0) + 1
                    
                    logger.info(f"✅ Email sent to {item.to_email}")
                else:
                    item.status = "failed"
                    item.error_message = result.get("error", "Unknown error")
                    item.retry_count = (item.retry_count or 0) + 1
                    failed_count += 1
                    
                    logger.error(f"❌ Failed to send to {item.to_email}: {item.error_message}")
                    
            except Exception as e:
                item.status = "failed"
                item.error_message = str(e)
                item.retry_count = (item.retry_count or 0) + 1
                failed_count += 1
                
                logger.error(f"❌ Exception sending to {item.to_email}: {e}")
        
        await session.commit()
    
    logger.info(f"📧 Scheduler complete: {sent_count} sent, {failed_count} failed")


async def start_email_scheduler():
    """
    הפעלת ה-scheduler
    רץ כל X דקות (לפי הגדרות)
    """
    logger.info("📧 Email Scheduler started")
    
    while True:
        try:
            settings = await get_settings()
            interval = settings.get('interval_minutes', 15)
            
            if settings.get('enabled', True):
                await send_scheduled_emails()
            
            # Wait for next interval
            await asyncio.sleep(interval * 60)
            
        except asyncio.CancelledError:
            logger.info("📧 Email Scheduler stopped")
            break
        except Exception as e:
            logger.error(f"📧 Scheduler error: {e}")
            # Wait 5 minutes before retry on error
            await asyncio.sleep(300)


async def retry_failed_emails():
    """
    ניסיון חוזר למיילים שנכשלו
    רץ פעם ביום
    """
    logger.info("📧 Retrying failed emails...")
    
    async with get_async_session_context() as session:
        # Get failed emails with less than 3 retries
        result = await session.execute(
            select(EmailQueue).where(
                and_(
                    EmailQueue.status == "failed",
                    EmailQueue.retry_count < 3
                )
            )
        )
        failed_items = result.scalars().all()
        
        for item in failed_items:
            # Reset to pending and reschedule for now
            item.status = "pending"
            item.scheduled_at = datetime.now()
            item.error_message = None
        
        await session.commit()
        
        logger.info(f"📧 {len(failed_items)} failed emails rescheduled for retry")


# For testing
if __name__ == "__main__":
    asyncio.run(send_scheduled_emails())
