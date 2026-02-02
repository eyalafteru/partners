"""
PartnerCalc OS - SMS Service
שליחת SMS דרך Twilio
"""
from typing import Optional, Dict, Any
from loguru import logger

from app.config import settings


class SMSService:
    """
    שירות שליחת SMS דרך Twilio
    https://www.twilio.com/
    """
    
    def __init__(
        self,
        account_sid: str = None,
        auth_token: str = None,
        phone_number: str = None
    ):
        self.account_sid = account_sid or settings.twilio_account_sid
        self.auth_token = auth_token or settings.twilio_auth_token
        self.from_number = phone_number or settings.twilio_phone_number
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
    
    async def send_sms(
        self,
        to_phone: str,
        message: str,
        status_callback: str = None
    ) -> Dict[str, Any]:
        """
        שליחת SMS
        
        Args:
            to_phone: מספר טלפון הנמען
            message: תוכן ההודעה (עד 160 תווים)
            status_callback: URL לקבלת עדכוני סטטוס
        
        Returns:
            {
                "success": True/False,
                "message_id": "...",
                "error": "..."
            }
        """
        import httpx
        
        # נרמול מספר טלפון
        to_phone = self._normalize_phone(to_phone)
        
        # וידוא אורך הודעה
        if len(message) > 160:
            logger.warning(f"SMS message too long ({len(message)} chars), truncating")
            message = message[:157] + "..."
        
        logger.info(f"Sending SMS to {to_phone}")
        
        url = f"{self.base_url}/Messages.json"
        
        auth = (self.account_sid, self.auth_token)
        
        data = {
            "To": to_phone,
            "From": self.from_number,
            "Body": message
        }
        
        if status_callback:
            data["StatusCallback"] = status_callback
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, data=data, auth=auth)
                result = response.json()
                
                if response.status_code == 201:
                    message_sid = result.get("sid")
                    logger.info(f"SMS sent successfully: {message_sid}")
                    return {
                        "success": True,
                        "message_id": message_sid
                    }
                else:
                    error = result.get("message", "Unknown error")
                    logger.error(f"SMS send failed: {error}")
                    return {
                        "success": False,
                        "error": error
                    }
                    
        except Exception as e:
            logger.error(f"SMS error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """
        קבלת סטטוס הודעה
        """
        import httpx
        
        url = f"{self.base_url}/Messages/{message_sid}.json"
        auth = (self.account_sid, self.auth_token)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, auth=auth)
                return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        קבלת יתרה בחשבון
        """
        import httpx
        
        url = f"{self.base_url}/Balance.json"
        auth = (self.account_sid, self.auth_token)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, auth=auth)
                result = response.json()
                
                return {
                    "balance": result.get("balance"),
                    "currency": result.get("currency")
                }
        except Exception as e:
            return {"error": str(e)}
    
    async def verify_connection(self) -> bool:
        """
        בדיקת חיבור ל-Twilio
        """
        import httpx
        
        url = f"{self.base_url}.json"
        auth = (self.account_sid, self.auth_token)
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, auth=auth)
                return response.status_code == 200
        except:
            return False
    
    def _normalize_phone(self, phone: str) -> str:
        """
        נרמול מספר טלפון לפורמט בינלאומי
        """
        # הסרת תווים מיותרים
        phone = phone.replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
        
        # וידוא שמתחיל ב-+
        if not phone.startswith("+"):
            if phone.startswith("972"):
                phone = "+" + phone
            elif phone.startswith("0"):
                phone = "+972" + phone[1:]
            else:
                phone = "+972" + phone
        
        return phone


# Singleton
_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    """קבלת instance של SMS service"""
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
