"""
PartnerCalc OS - WhatsApp Notification Service
שליחת התראות WhatsApp דרך Green API
"""
import httpx
from loguru import logger
from typing import List, Optional
from app.config import settings


class WhatsAppService:
    """שירות שליחת הודעות WhatsApp דרך Green API"""
    
    def __init__(self):
        self.api_url = settings.greenapi_url
        self.instance_id = settings.greenapi_instance_id
        self.api_token = settings.greenapi_api_token
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.api_url and self.instance_id and self.api_token)
    
    async def send_to_phone(self, phone: str, message: str) -> dict:
        """
        שליחת הודעת WhatsApp למספר ספציפי.
        מחזיר dict: {"success": bool, "message_id": str|None, "error": str|None}
        """
        if not self.is_configured:
            logger.warning("📱 WhatsApp not configured - skipping notification")
            return {"success": False, "message_id": None, "error": "WhatsApp not configured"}
        
        try:
            url = f"{self.api_url}/waInstance{self.instance_id}/sendMessage/{self.api_token}"
            
            # פורמט מספר הטלפון
            phone_clean = phone.replace("+", "").replace("-", "").replace(" ", "")
            if phone_clean.startswith("0"):
                phone_clean = "972" + phone_clean[1:]
            if not phone_clean.endswith("@c.us"):
                phone_clean = f"{phone_clean}@c.us"
            
            payload = {
                "chatId": phone_clean,
                "message": message
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    message_id = data.get("idMessage")
                    logger.info(f"📱 ✅ WhatsApp sent to {phone}")
                    return {"success": True, "message_id": message_id, "error": None}
                else:
                    error_msg = f"HTTP {response.status_code}"
                    logger.error(f"📱 ❌ WhatsApp failed for {phone}: {error_msg}")
                    return {"success": False, "message_id": None, "error": error_msg}
        
        except Exception as e:
            logger.error(f"📱 ❌ WhatsApp error for {phone}: {e}")
            return {"success": False, "message_id": None, "error": str(e)}
    
    async def send_to_all_active(self, message: str, email_id: int = None) -> List[dict]:
        """שליחת הודעה לכל המספרים הפעילים"""
        from app.database import SessionLocal
        from app.models.notifications import NotificationPhone, NotificationLog
        from sqlalchemy import select
        
        results = []
        
        try:
            with SessionLocal() as db:
                # שליפת כל המספרים הפעילים
                phones = db.execute(
                    select(NotificationPhone).where(NotificationPhone.is_active == True)
                ).scalars().all()
                
                if not phones:
                    logger.warning("📱 No active notification phones configured")
                    return results
                
                logger.info(f"📱 Sending WhatsApp to {len(phones)} phones...")
                
                for phone_obj in phones:
                    send_result = await self.send_to_phone(phone_obj.phone, message)
                    success = send_result.get("success", False)
                    
                    # שמירת לוג
                    log = NotificationLog(
                        phone=phone_obj.phone,
                        message=message[:500],
                        status="sent" if success else "failed",
                        related_email_id=email_id
                    )
                    db.add(log)
                    
                    results.append({
                        "phone": phone_obj.phone,
                        "name": phone_obj.name,
                        "success": success
                    })
                
                db.commit()
                logger.info(f"📱 WhatsApp notifications completed: {len(results)} sent")
        
        except Exception as e:
            logger.error(f"📱 Failed to send notifications: {e}")
        
        return results
    
    async def send_new_email_alert(self, from_email: str, subject: str, lead_domain: str = None, email_id: int = None):
        """שליחת התראה על מייל חדש לכל המספרים"""
        message = f"""🔔 *מייל חדש התקבל!*

📧 *מאת:* {from_email}
📝 *נושא:* {subject}
🌐 *אתר:* {lead_domain or 'לא ידוע'}

👉 כנס למערכת לצפייה:
http://partners.ppcmedia.co.il/leads"""
        
        return await self.send_to_all_active(message, email_id)
    
    async def send_facebook_comment_alert(
        self,
        group_name: str,
        commenter_name: str,
        comment_text: str,
        suggested_response: str = None,
        post_id: int = None,
        interest_level: str = None
    ):
        """שליחת התראה על תגובה חדשה בפייסבוק"""
        comment_preview = comment_text[:150] + "..." if len(comment_text) > 150 else comment_text
        
        # אינדיקטור interest level
        interest_indicator = ""
        if interest_level == "high":
            interest_indicator = " 🔥 *עניין גבוה!*"
        elif interest_level == "medium":
            interest_indicator = " ⭐ עניין בינוני"
        
        message = f"""📱 *תגובה חדשה בפייסבוק!*{interest_indicator}

📁 *קבוצה:* {group_name}
👤 *מגיב:* {commenter_name}
💬 *תגובה:* {comment_preview}"""
        
        if suggested_response:
            response_preview = suggested_response[:200] + "..." if len(suggested_response) > 200 else suggested_response
            message += f"""

🤖 *הצעת תשובה (ממתינה לאישור):*
{response_preview}"""
        
        message += """

👉 כנס למערכת לאישור:
http://partners.ppcmedia.co.il/facebook-marketing"""
        
        return await self.send_to_all_active(message)


# Singleton
_whatsapp_service = None


def get_whatsapp_service() -> WhatsAppService:
    """קבלת instance של WhatsApp Service"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
