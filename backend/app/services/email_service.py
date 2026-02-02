"""
PartnerCalc OS - Email Service
שליחת מיילים דרך SendGrid
"""
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings


class EmailService:
    """
    שירות שליחת Email דרך SendGrid
    https://sendgrid.com/
    """
    
    def __init__(self, api_key: str = None, from_email: str = None, from_name: str = None):
        self.api_key = api_key or settings.sendgrid_api_key
        self.from_email = from_email or settings.email_from
        self.from_name = from_name or settings.email_from_name
    
    def _wrap_in_rtl_html(self, text: str) -> str:
        """עטיפת טקסט ב-HTML עם תמיכה ב-RTL ועיצוב יפה"""
        import re
        
        # שלב 1: עיצוב טקסט (לפני הוספת HTML)
        # החלפת טקסט בין גרשיים לבולד
        text = re.sub(r'"([^"]+)"', r'<strong>"\1"</strong>', text)
        
        # החלפת אימוג'י כותרות לבולד
        text = re.sub(r'(🎁[^\n]+)', r'<strong>\1</strong>', text)
        text = re.sub(r'(💡[^\n]+)', r'<strong style="color: #1e5490;">\1</strong>', text)
        text = re.sub(r'(🔍[^\n]+)', r'<strong style="color: #1e5490;">\1</strong>', text)
        text = re.sub(r'(✨[^\n]+)', r'<strong style="color: #6b46c1;">\1</strong>', text)
        
        # שלב 2: המרת URLs לקישורים לחיצים
        def url_to_link(match):
            url = match.group(1)
            return f'<a href="{url}" style="color: #1e5490; text-decoration: underline;">{url}</a>'
        
        text = re.sub(r'(https?://[^\s<>"]+)', url_to_link, text)
        
        # המרת שורות חדשות לפסקאות
        paragraphs = text.split('\n\n')
        html_paragraphs = []
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            
            # בדיקה אם זו רשימה עם נקודות
            if p.startswith('•') or '\n•' in p:
                # המרת רשימה ל-<ul>
                items = p.split('\n')
                list_items = []
                for item in items:
                    item = item.strip()
                    if item.startswith('•'):
                        item = item[1:].strip()
                        list_items.append(f'<li style="margin-bottom: 8px;">{item}</li>')
                    elif item:
                        list_items.append(f'<li style="margin-bottom: 8px;">{item}</li>')
                if list_items:
                    html_paragraphs.append(f'<ul style="margin: 15px 0; padding-right: 20px; list-style-type: disc;">{"".join(list_items)}</ul>')
            else:
                # פסקה רגילה
                p = p.replace('\n', '<br>')
                html_paragraphs.append(f'<p style="margin: 0 0 20px 0;">{p}</p>')
        
        body_content = '\n'.join(html_paragraphs)
        
        return f'''<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="
    direction: rtl;
    text-align: right;
    font-family: Arial, 'Helvetica Neue', Helvetica, sans-serif;
    font-size: 16px;
    line-height: 1.8;
    color: #333333;
    padding: 30px;
    max-width: 600px;
    margin: 0 auto;
    background-color: #ffffff;
">
<div style="padding: 20px;">
{body_content}

<div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e5e5;">
    <p style="margin: 0; font-weight: bold;">אייל עובדיה</p>
    <p style="margin: 5px 0 0 0;">
        <strong>רק תבקש</strong> | 
        <a href="https://loan-israel.co.il" style="color: #1e5490; text-decoration: none;">loan-israel.co.il</a>
    </p>
</div>
</div>
</body>
</html>'''

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str = None,
        reply_to: str = None
    ) -> Dict[str, Any]:
        """
        שליחת מייל
        
        Args:
            to_email: כתובת הנמען
            subject: נושא
            body: גוף ההודעה (טקסט)
            html_body: גוף ההודעה (HTML) - אופציונלי
            reply_to: כתובת לתשובות
        
        Returns:
            {
                "success": True/False,
                "message_id": "...",
                "error": "..."
            }
        """
        import httpx
        
        logger.info(f"Sending email to {to_email}: {subject}")
        
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # אם אין HTML - יצירת HTML אוטומטית עם RTL
        if not html_body:
            html_body = self._wrap_in_rtl_html(body)
        
        # בניית הודעה - HTML קודם (עדיפות גבוהה יותר)
        content = [
            {"type": "text/plain", "value": body},
            {"type": "text/html", "value": html_body}
        ]
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "subject": subject
                }
            ],
            "from": {
                "email": self.from_email,
                "name": self.from_name
            },
            "content": content,
            "tracking_settings": {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True}
            }
        }
        
        if reply_to:
            payload["reply_to"] = {"email": reply_to}
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code in [200, 202]:
                    message_id = response.headers.get("X-Message-Id", "")
                    logger.info(f"Email sent successfully: {message_id}")
                    return {
                        "success": True,
                        "message_id": message_id
                    }
                else:
                    error = response.text
                    logger.error(f"Email send failed: {error}")
                    return {
                        "success": False,
                        "error": error
                    }
                    
        except Exception as e:
            logger.error(f"Email error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_template(
        self,
        to_email: str,
        template_id: str,
        dynamic_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        שליחת מייל מתבנית SendGrid
        """
        import httpx
        
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}],
                    "dynamic_template_data": dynamic_data
                }
            ],
            "from": {
                "email": self.from_email,
                "name": self.from_name
            },
            "template_id": template_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code in [200, 202]:
                    return {"success": True}
                else:
                    return {"success": False, "error": response.text}
                    
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def verify_connection(self) -> bool:
        """
        בדיקת חיבור ל-SendGrid
        """
        import httpx
        
        url = "https://api.sendgrid.com/v3/user/credits"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except:
            return False


# Singleton
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """קבלת instance של Email service"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
