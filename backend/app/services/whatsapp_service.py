"""
PartnerCalc OS - WhatsApp Service
שליחת הודעות WhatsApp דרך Green-API
"""
import httpx
from typing import Optional, Dict, Any
from loguru import logger

from app.config import settings


class WhatsAppService:
    """
    שירות שליחת WhatsApp דרך Green-API
    https://green-api.com/
    """
    
    def __init__(self, instance_id: str = None, token: str = None):
        self.instance_id = instance_id or settings.green_api_instance
        self.token = token or settings.green_api_token
        self.base_url = f"https://api.green-api.com/waInstance{self.instance_id}"
    
    async def send_message(
        self,
        phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        שליחת הודעת WhatsApp
        
        Args:
            phone: מספר טלפון (עם או בלי קידומת)
            message: תוכן ההודעה
        
        Returns:
            {
                "success": True/False,
                "message_id": "...",
                "error": "..."
            }
        """
        # נרמול מספר טלפון
        phone = self._normalize_phone(phone)
        
        url = f"{self.base_url}/sendMessage/{self.token}"
        
        payload = {
            "chatId": f"{phone}@c.us",
            "message": message
        }
        
        logger.info(f"Sending WhatsApp to {phone}")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                result = response.json()
                
                if response.status_code == 200 and result.get("idMessage"):
                    logger.info(f"WhatsApp sent successfully: {result['idMessage']}")
                    return {
                        "success": True,
                        "message_id": result["idMessage"]
                    }
                else:
                    error = result.get("message", "Unknown error")
                    logger.error(f"WhatsApp send failed: {error}")
                    return {
                        "success": False,
                        "error": error
                    }
                    
        except Exception as e:
            logger.error(f"WhatsApp error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_file(
        self,
        phone: str,
        file_url: str,
        filename: str,
        caption: str = None
    ) -> Dict[str, Any]:
        """
        שליחת קובץ ב-WhatsApp
        """
        phone = self._normalize_phone(phone)
        
        url = f"{self.base_url}/sendFileByUrl/{self.token}"
        
        payload = {
            "chatId": f"{phone}@c.us",
            "urlFile": file_url,
            "fileName": filename
        }
        
        if caption:
            payload["caption"] = caption
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload)
                result = response.json()
                
                if response.status_code == 200:
                    return {"success": True, "message_id": result.get("idMessage")}
                else:
                    return {"success": False, "error": result.get("message")}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def check_phone(self, phone: str) -> bool:
        """
        בדיקה אם מספר טלפון מחובר ל-WhatsApp
        """
        phone = self._normalize_phone(phone)
        
        url = f"{self.base_url}/checkWhatsapp/{self.token}"
        
        payload = {
            "phoneNumber": int(phone)
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, json=payload)
                result = response.json()
                
                return result.get("existsWhatsapp", False)
                
        except Exception as e:
            logger.error(f"Check WhatsApp error: {e}")
            return False
    
    async def get_state(self) -> Dict[str, Any]:
        """
        בדיקת מצב החשבון
        """
        url = f"{self.base_url}/getStateInstance/{self.token}"
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def verify_connection(self) -> bool:
        """
        בדיקה אם החשבון מחובר
        """
        state = await self.get_state()
        return state.get("stateInstance") == "authorized"
    
    def _normalize_phone(self, phone: str) -> str:
        """
        נרמול מספר טלפון לפורמט ישראלי
        """
        # הסרת תווים מיותרים
        phone = phone.replace("-", "").replace(" ", "").replace("+", "")
        
        # הסרת 972 או 0 בהתחלה והוספת 972
        if phone.startswith("972"):
            pass  # כבר בפורמט נכון
        elif phone.startswith("0"):
            phone = "972" + phone[1:]
        else:
            phone = "972" + phone
        
        return phone


# Singleton
_whatsapp_service: Optional[WhatsAppService] = None


def get_whatsapp_service() -> WhatsAppService:
    """קבלת instance של WhatsApp service"""
    global _whatsapp_service
    if _whatsapp_service is None:
        _whatsapp_service = WhatsAppService()
    return _whatsapp_service
