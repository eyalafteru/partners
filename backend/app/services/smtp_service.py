"""
PartnerCalc OS - SMTP Email Service
שליחת מיילים דרך SMTP (חלופה ל-SendGrid)
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import settings

import os

# Base URL for tracking - from environment or Cloudflare Tunnel
# עדכן ב-.env או כמשתנה סביבה
TRACKING_BASE_URL = os.getenv(
    "TRACKING_BASE_URL", 
    "https://partners.ppcmedia.co.il/api/tracking"
)


class SMTPService:
    """
    שירות שליחת מיילים דרך SMTP
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        use_ssl: bool = True,
        from_name: str = None
    ):
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username or settings.smtp_user
        self.password = password or settings.smtp_password
        self.use_ssl = use_ssl
        self.from_name = from_name or settings.email_from_name
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def _generate_tracking_id(self, communication_id: int) -> str:
        """יצירת מזהה מעקב"""
        import base64
        import hashlib
        data = f"{communication_id}:partnercalc"
        return base64.urlsafe_b64encode(
            hashlib.sha256(data.encode()).digest()[:12] + 
            str(communication_id).encode()
        ).decode().rstrip("=")
    
    def _inject_tracking(self, html_body: str, communication_id: int) -> str:
        """הזרקת מעקב ל-HTML"""
        import re
        from urllib.parse import quote
        
        tracking_id = self._generate_tracking_id(communication_id)
        
        # 1. הוספת Tracking Pixel לפני סגירת </body>
        pixel_url = f"{TRACKING_BASE_URL}/pixel/{tracking_id}.gif"
        pixel_html = f'<img src="{pixel_url}" width="1" height="1" style="display:none" alt="" />'
        
        if "</body>" in html_body:
            html_body = html_body.replace("</body>", f"{pixel_html}</body>")
        else:
            html_body += pixel_html
        
        # 2. החלפת קישורים לקישורי מעקב
        def replace_link(match):
            original_url = match.group(1)
            # לא להחליף קישורי mailto ו-tel
            if original_url.startswith(("mailto:", "tel:", "#")):
                return match.group(0)
            # לא להחליף את קישורי המעקב עצמם
            if TRACKING_BASE_URL in original_url:
                return match.group(0)
            
            encoded_url = quote(original_url, safe="")
            tracked_url = f"{TRACKING_BASE_URL}/click/{tracking_id}?url={encoded_url}"
            return f'href="{tracked_url}"'
        
        html_body = re.sub(r'href="([^"]+)"', replace_link, html_body)
        html_body = re.sub(r"href='([^']+)'", replace_link, html_body)
        
        return html_body
    
    def _connect(self) -> smtplib.SMTP_SSL:
        """התחברות לשרת SMTP"""
        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=30)
            else:
                server = smtplib.SMTP(self.host, self.port, timeout=30)
                server.starttls()
            
            server.login(self.username, self.password)
            logger.info(f"✅ Connected to SMTP: {self.host}")
            return server
        except Exception as e:
            logger.error(f"❌ SMTP connection failed: {e}")
            raise
    
    def _wrap_in_rtl_html(self, text: str) -> str:
        """עטיפת טקסט ב-HTML עם תמיכה ב-RTL"""
        import re
        
        # עיצוב טקסט
        text = re.sub(r'"([^"]+)"', r'<strong>"\1"</strong>', text)
        text = re.sub(r'(🎁[^\n]+)', r'<strong>\1</strong>', text)
        text = re.sub(r'(💡[^\n]+)', r'<strong style="color: #1e5490;">\1</strong>', text)
        
        # המרת URLs לקישורים
        def url_to_link(match):
            url = match.group(1)
            return f'<a href="{url}" style="color: #1e5490; text-decoration: underline;">{url}</a>'
        
        text = re.sub(r'(https?://[^\s<>"]+)', url_to_link, text)
        
        # המרת שורות חדשות
        paragraphs = text.split('\n\n')
        html_paragraphs = []
        
        for p in paragraphs:
            p = p.strip()
            if not p:
                continue
            
            if p.startswith('•') or '\n•' in p:
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
                    html_paragraphs.append(f'<ul style="margin: 15px 0; padding-right: 20px;">{"".join(list_items)}</ul>')
            else:
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
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: str = None,
        reply_to: str = None,
        cc: List[str] = None,
        bcc: List[str] = None,
        communication_id: int = None,
        enable_tracking: bool = True
    ) -> Dict[str, Any]:
        """
        שליחת מייל
        
        Args:
            to_email: כתובת הנמען
            subject: נושא
            body: גוף ההודעה (טקסט)
            html_body: גוף ההודעה (HTML) - אופציונלי
            reply_to: כתובת לתשובות
            cc: עותקים
            bcc: עותקים מוסתרים
        
        Returns:
            {"success": True/False, "message_id": "...", "error": "..."}
        """
        logger.info(f"📧 Sending email to {to_email}: {subject}")
        
        try:
            # יצירת הודעה
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.username))
            msg['To'] = to_email
            msg['Date'] = formatdate(localtime=True)
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            # הוספת גוף טקסט
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # הוספת גוף HTML
            if not html_body:
                html_body = self._wrap_in_rtl_html(body)
            
            # הזרקת מעקב אם יש communication_id
            if enable_tracking and communication_id:
                html_body = self._inject_tracking(html_body, communication_id)
            
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # רשימת נמענים
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # שליחה
            server = self._connect()
            try:
                server.sendmail(self.username, recipients, msg.as_string())
                message_id = msg.get('Message-ID', f"{datetime.utcnow().timestamp()}@{self.host}")
                logger.info(f"✅ Email sent successfully to {to_email}")
                
                return {
                    "success": True,
                    "message_id": message_id
                }
            finally:
                server.quit()
        
        except Exception as e:
            logger.error(f"❌ Email send failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_email_async(self, **kwargs) -> Dict[str, Any]:
        """גרסה אסינכרונית של send_email"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.send_email(**kwargs)
        )
    
    def verify_connection(self) -> bool:
        """בדיקת חיבור"""
        try:
            server = self._connect()
            server.quit()
            return True
        except:
            return False


# Singleton
_smtp_service: Optional[SMTPService] = None


def get_smtp_service() -> SMTPService:
    """קבלת instance של SMTP service"""
    global _smtp_service
    if _smtp_service is None:
        _smtp_service = SMTPService()
    return _smtp_service
