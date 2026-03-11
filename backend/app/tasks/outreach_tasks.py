"""
PartnerCalc OS - Outreach Tasks
משימות פנייה ללידים
"""
from celery import shared_task
from datetime import datetime
from loguru import logger

from app.database import SyncSessionLocal
from app.models.lead import Lead
from app.models.calculator import Calculator
from app.models.communication import Communication


@shared_task(bind=True)
def send_outreach_whatsapp(self, lead_id: int, message: str = None):
    """
    שליחת הודעת WhatsApp לליד
    """
    session = SyncSessionLocal()
    
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            logger.error(f"Lead {lead_id} not found")
            return
        
        # קבלת מספר טלפון
        phones = lead.contact_info.get("phones", [])
        if not phones:
            logger.warning(f"No phone for lead {lead_id}")
            return {"success": False, "error": "No phone number"}
        
        phone = phones[0]
        
        # אם אין הודעה - יצירה אוטומטית עם AI
        if not message:
            calc = None
            if lead.recommended_calc_id:
                calc = session.query(Calculator).get(lead.recommended_calc_id)
            
            if calc:
                import asyncio
                from app.services.ai_service import AIService
                
                # TODO: צור session async
                # message = await ai_service.generate_whatsapp(lead, calc)
                message = f"היי! ראיתי את האתר {lead.site_name or lead.domain} ויש לי הצעה מעניינת בשבילך..."
        
        # שליחה
        from app.services.whatsapp_service import get_whatsapp_service
        import asyncio
        
        wa = get_whatsapp_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(wa.send_to_phone(phone, message))
        loop.close()
        
        # שמירת התקשורת
        comm = Communication(
            lead_id=lead_id,
            channel="whatsapp",
            direction="outbound",
            message_body=message,
            status="sent" if result["success"] else "failed",
            external_id=result.get("message_id"),
            error_message=result.get("error"),
            sent_at=datetime.utcnow()
        )
        session.add(comm)
        
        # עדכון סטטוס הליד
        if result["success"]:
            lead.status = "contacted"
            lead.last_contacted_at = datetime.utcnow()
        
        session.commit()
        
        return result
        
    finally:
        session.close()


@shared_task(bind=True)
def send_outreach_email(self, lead_id: int, subject: str = None, body: str = None):
    """
    שליחת Email לליד
    """
    session = SyncSessionLocal()
    
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
        
        # קבלת מייל
        emails = lead.contact_info.get("emails", [])
        if not emails:
            return {"success": False, "error": "No email"}
        
        email = emails[0]
        
        # אם אין תוכן - יצירה אוטומטית
        if not subject or not body:
            subject = subject or f"הצעת שיתוף פעולה - {lead.site_name or lead.domain}"
            body = body or f"שלום,\n\nראיתי את האתר {lead.domain} ורציתי להציע לך שיתוף פעולה..."
        
        # שליחה
        from app.services.smtp_service import get_smtp_service
        import asyncio
        
        smtp_service = get_smtp_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(smtp_service.send_email_async(to_email=email, subject=subject, body=body))
        loop.close()
        
        # שמירה
        comm = Communication(
            lead_id=lead_id,
            channel="email",
            direction="outbound",
            message_body=body,
            subject=subject,
            status="sent" if result["success"] else "failed",
            external_id=result.get("message_id"),
            error_message=result.get("error"),
            sent_at=datetime.utcnow()
        )
        session.add(comm)
        
        if result["success"]:
            lead.status = "contacted"
            lead.last_contacted_at = datetime.utcnow()
        
        session.commit()
        
        return result
        
    finally:
        session.close()


@shared_task(bind=True)
def send_outreach_sms(self, lead_id: int, message: str = None):
    """
    שליחת SMS לליד
    """
    session = SyncSessionLocal()
    
    try:
        lead = session.query(Lead).get(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}
        
        phones = lead.contact_info.get("phones", [])
        if not phones:
            return {"success": False, "error": "No phone"}
        
        phone = phones[0]
        
        if not message:
            message = f"היי! יש לי הצעה מעניינת לאתר {lead.domain}. נדבר?"
        
        # וידוא אורך
        if len(message) > 160:
            message = message[:157] + "..."
        
        from app.services.sms_service import get_sms_service
        import asyncio
        
        sms = get_sms_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(sms.send_sms(phone, message))
        loop.close()
        
        comm = Communication(
            lead_id=lead_id,
            channel="sms",
            direction="outbound",
            message_body=message,
            status="sent" if result["success"] else "failed",
            external_id=result.get("message_id"),
            error_message=result.get("error"),
            sent_at=datetime.utcnow()
        )
        session.add(comm)
        
        if result["success"]:
            lead.status = "contacted"
            lead.last_contacted_at = datetime.utcnow()
        
        session.commit()
        
        return result
        
    finally:
        session.close()


@shared_task
def send_bulk_outreach(lead_ids: list, channel: str = "whatsapp"):
    """
    שליחת פניות לרשימת לידים
    """
    results = {"success": 0, "failed": 0}
    
    for lead_id in lead_ids:
        try:
            if channel == "whatsapp":
                send_outreach_whatsapp.delay(lead_id)
            elif channel == "email":
                send_outreach_email.delay(lead_id)
            elif channel == "sms":
                send_outreach_sms.delay(lead_id)
            
            results["success"] += 1
            
        except Exception as e:
            logger.error(f"Failed to queue outreach for {lead_id}: {e}")
            results["failed"] += 1
    
    return results
