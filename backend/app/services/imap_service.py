"""
PartnerCalc OS - IMAP Email Service
קריאת מיילים נכנסים מתיבת דואר
"""
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.config import settings


class IMAPService:
    """
    שירות קריאת מיילים דרך IMAP
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        use_ssl: bool = True
    ):
        self.host = host or settings.imap_host
        self.port = port or settings.imap_port
        self.username = username or settings.imap_user
        self.password = password or settings.imap_password
        self.use_ssl = use_ssl
        self._connection = None
        self._executor = ThreadPoolExecutor(max_workers=2)
    
    def _connect(self) -> imaplib.IMAP4_SSL:
        """התחברות לשרת IMAP"""
        try:
            if self.use_ssl:
                conn = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                conn = imaplib.IMAP4(self.host, self.port)
            
            conn.login(self.username, self.password)
            logger.info(f"✅ Connected to IMAP: {self.username}")
            return conn
        except Exception as e:
            logger.error(f"❌ IMAP connection failed: {e}")
            raise
    
    def _disconnect(self, conn: imaplib.IMAP4_SSL):
        """ניתוק מהשרת"""
        try:
            conn.logout()
        except:
            pass
    
    def _decode_header_value(self, value: str) -> str:
        """פענוח כותרת מייל (תמיכה ב-UTF-8, Hebrew, etc.)"""
        if not value:
            return ""
        
        decoded_parts = decode_header(value)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(encoding or 'utf-8', errors='replace'))
                except:
                    result.append(part.decode('utf-8', errors='replace'))
            else:
                result.append(part)
        
        return ''.join(result)
    
    def _get_email_body(self, msg) -> Dict[str, str]:
        """חילוץ תוכן המייל (טקסט ו-HTML)"""
        text_body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # דלג על קבצים מצורפים
                if "attachment" in content_disposition:
                    continue
                
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        charset = part.get_content_charset() or 'utf-8'
                        decoded = payload.decode(charset, errors='replace')
                        
                        if content_type == "text/plain":
                            text_body = decoded
                        elif content_type == "text/html":
                            html_body = decoded
                except Exception as e:
                    logger.warning(f"Failed to decode email part: {e}")
        else:
            # מייל פשוט ללא multipart
            try:
                payload = msg.get_payload(decode=True)
                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    text_body = payload.decode(charset, errors='replace')
            except Exception as e:
                logger.warning(f"Failed to decode email body: {e}")
        
        return {"text": text_body, "html": html_body}
    
    def _get_attachments(self, msg) -> List[Dict[str, Any]]:
        """חילוץ רשימת קבצים מצורפים"""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                        attachments.append({
                            "filename": filename,
                            "content_type": part.get_content_type(),
                            "size": len(part.get_payload(decode=True) or b"")
                        })
        
        return attachments
    
    def _parse_email(self, msg_data: bytes, uid: str) -> Dict[str, Any]:
        """פירוש מייל לאובייקט Python"""
        msg = email.message_from_bytes(msg_data)
        
        # חילוץ שדות בסיסיים
        from_raw = msg.get("From", "")
        to_raw = msg.get("To", "")
        subject = self._decode_header_value(msg.get("Subject", ""))
        date_str = msg.get("Date", "")
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")
        
        # פירוש כתובות
        from_email = ""
        from_name = ""
        import re
        email_match = re.search(r'[\w\.-]+@[\w\.-]+', from_raw)
        if email_match:
            from_email = email_match.group()
        name_match = re.match(r'^"?([^"<]+)"?\s*<', from_raw)
        if name_match:
            from_name = name_match.group(1).strip()
        
        # פירוש תאריך
        received_at = None
        if date_str:
            try:
                received_at = parsedate_to_datetime(date_str)
            except:
                received_at = datetime.utcnow()
        
        # חילוץ תוכן
        body = self._get_email_body(msg)
        attachments = self._get_attachments(msg)
        
        return {
            "uid": uid,
            "message_id": message_id.strip("<>"),
            "from_email": from_email,
            "from_name": from_name,
            "to": to_raw,
            "subject": subject,
            "text_body": body["text"],
            "html_body": body["html"],
            "received_at": received_at,
            "in_reply_to": in_reply_to.strip("<>") if in_reply_to else None,
            "references": references,
            "attachments": attachments,
            "has_attachments": len(attachments) > 0
        }
    
    def fetch_new_emails(
        self,
        folder: str = "INBOX",
        since_date: datetime = None,
        limit: int = 50,
        mark_as_read: bool = False
    ) -> List[Dict[str, Any]]:
        """
        שליפת מיילים חדשים מהתיבה
        
        Args:
            folder: תיקייה לסריקה (INBOX, Sent, etc.)
            since_date: משוך רק מיילים מתאריך זה
            limit: מקסימום מיילים למשוך
            mark_as_read: האם לסמן כנקראו
        
        Returns:
            רשימת מיילים
        """
        conn = self._connect()
        emails = []
        
        try:
            # בחירת תיקייה
            conn.select(folder)
            
            # בניית שאילתת חיפוש
            if since_date:
                date_str = since_date.strftime("%d-%b-%Y")
                search_criteria = f'(SINCE {date_str})'
            else:
                search_criteria = 'ALL'
            
            # חיפוש
            status, message_ids = conn.search(None, search_criteria)
            
            if status != "OK":
                logger.warning(f"IMAP search failed: {status}")
                return []
            
            # המרה לרשימה
            id_list = message_ids[0].split()
            
            # הגבלת כמות (מהאחרונים)
            if len(id_list) > limit:
                id_list = id_list[-limit:]
            
            logger.info(f"📬 Found {len(id_list)} emails in {folder}")
            
            # שליפת כל מייל
            for msg_id in id_list:
                try:
                    # קבלת UID
                    status, uid_data = conn.fetch(msg_id, '(UID)')
                    uid = uid_data[0].decode().split('UID ')[1].split(')')[0]
                    
                    # קבלת תוכן המייל
                    status, msg_data = conn.fetch(msg_id, '(RFC822)')
                    
                    if status == "OK" and msg_data[0]:
                        raw_email = msg_data[0][1]
                        parsed = self._parse_email(raw_email, uid)
                        emails.append(parsed)
                        
                        # סימון כנקרא אם נדרש
                        if mark_as_read:
                            conn.store(msg_id, '+FLAGS', '\\Seen')
                
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg_id}: {e}")
                    continue
            
        finally:
            self._disconnect(conn)
        
        # מיון לפי תאריך (חדשים קודם)
        emails.sort(key=lambda x: x.get('received_at') or datetime.min, reverse=True)
        
        return emails
    
    def fetch_unread_emails(self, folder: str = "INBOX", limit: int = 50) -> List[Dict[str, Any]]:
        """שליפת מיילים שלא נקראו בלבד"""
        conn = self._connect()
        emails = []
        
        try:
            conn.select(folder)
            
            # חיפוש רק לא נקראו
            status, message_ids = conn.search(None, 'UNSEEN')
            
            if status != "OK":
                return []
            
            id_list = message_ids[0].split()
            
            if len(id_list) > limit:
                id_list = id_list[-limit:]
            
            logger.info(f"📬 Found {len(id_list)} unread emails")
            
            for msg_id in id_list:
                try:
                    status, uid_data = conn.fetch(msg_id, '(UID)')
                    uid = uid_data[0].decode().split('UID ')[1].split(')')[0]
                    
                    status, msg_data = conn.fetch(msg_id, '(RFC822)')
                    
                    if status == "OK" and msg_data[0]:
                        raw_email = msg_data[0][1]
                        parsed = self._parse_email(raw_email, uid)
                        emails.append(parsed)
                
                except Exception as e:
                    logger.warning(f"Failed to fetch email {msg_id}: {e}")
                    continue
            
        finally:
            self._disconnect(conn)
        
        emails.sort(key=lambda x: x.get('received_at') or datetime.min, reverse=True)
        return emails
    
    def get_folder_list(self) -> List[str]:
        """קבלת רשימת תיקיות"""
        conn = self._connect()
        folders = []
        
        try:
            status, folder_list = conn.list()
            
            if status == "OK":
                for folder_data in folder_list:
                    # פירוש שם התיקייה
                    folder_str = folder_data.decode()
                    # חילוץ שם (בסוף, אחרי הריווח האחרון)
                    parts = folder_str.split(' "/" ')
                    if len(parts) > 1:
                        folder_name = parts[-1].strip('"')
                        folders.append(folder_name)
        
        finally:
            self._disconnect(conn)
        
        return folders
    
    async def fetch_new_emails_async(self, **kwargs) -> List[Dict[str, Any]]:
        """גרסה אסינכרונית של fetch_new_emails"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.fetch_new_emails(**kwargs)
        )
    
    async def fetch_unread_emails_async(self, **kwargs) -> List[Dict[str, Any]]:
        """גרסה אסינכרונית של fetch_unread_emails"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: self.fetch_unread_emails(**kwargs)
        )
    
    def verify_connection(self) -> bool:
        """בדיקת חיבור"""
        try:
            conn = self._connect()
            self._disconnect(conn)
            return True
        except:
            return False


# Singleton
_imap_service: Optional[IMAPService] = None


def get_imap_service() -> IMAPService:
    """קבלת instance של IMAP service"""
    global _imap_service
    if _imap_service is None:
        _imap_service = IMAPService()
    return _imap_service
