"""
PartnerCalc OS - WhatsApp Notification Service
שליחת התראות WhatsApp דרך Green API
"""
import httpx
from loguru import logger
from app.config import settings


class WhatsAppService:
    """שירות שליחת הודעות WhatsApp דרך Green API"""
    
    def __init__(self):
        self.api_url = settings.greenapi_url
        self.instance_id = settings.greenapi_instance_id
        self.api_token = settings.greenapi_api_token
        self.notify_phone = settings.greenapi_notify_phone
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.api_url and self.instance_id and self.api_token and self.notify_phone)
    
    async def send_notification(self, message: str) -> bool:
        """שליחת הודעת WhatsApp"""
        if not self.is_configured:
            logger.warning("📱 WhatsApp not configured - skipping notification")
            return False
        
        try:
            url = f"{self.api_url}/waInstance{self.instance_id}/sendMessage/{self.api_token}"
            
            # פורמט מספר הטלפון (צריך להיות עם קידומת מדינה, בלי +)
            phone = self.notify_phone.replace("+", "").replace("-", "").replace(" ", "")
            if not phone.endswith("@c.us"):
                phone = f"{phone}@c.us"
            
            payload = {
                "chatId": phone,
                "message": message
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.info(f"📱 ✅ WhatsApp notification sent successfully")
                    return True
                else:
                    logger.error(f"📱 ❌ WhatsApp send failed: {response.status_code} - {response.text}")
                    return False
        
        except Exception as e:
            logger.error(f"📱 ❌ WhatsApp error: {e}")
            return False
    
    async def send_new_email_alert(self, from_email: str, subject: str, lead_domain: str = None):
        """שליחת התראה על מייל חדש"""
        message = f"""🔔 *מייל חדש התקבל!*

📧 *מאת:* {from_email}
📝 *נושא:* {subject}
🌐 *אתר:* {lead_domain or 'לא ידוע'}

👉 כנס למערכת לצפייה:
http://partners.ppcmedia.co.il/leads"""
        
        return await self.send_notification(message)


# Singleton
_whatsapp_service = None


def get_whatsapp_service() -> WhatsAppService:
    """קבלת instance של WhatsApp Service"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
