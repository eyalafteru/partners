"""
PartnerCalc OS - DrissionPage Scraper
סריקת אתרים עם DrissionPage
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings


class StealthScraper:
    """
    סורק אתרים עם DrissionPage
    תומך ב-Stealth Mode לעקיפת הגנות
    """
    
    def __init__(self, proxy_url: str = None, headless: bool = True):
        self.proxy_url = proxy_url or settings.proxy_service_url
        self.headless = headless
        self._page = None
    
    def _get_page(self):
        """יצירת page חדש"""
        from DrissionPage import ChromiumPage, ChromiumOptions
        
        options = ChromiumOptions()
        
        if self.headless:
            options.headless(True)
        
        # Stealth settings
        options.set_argument('--disable-blink-features=AutomationControlled')
        options.set_argument('--no-sandbox')
        options.set_argument('--disable-dev-shm-usage')
        options.set_argument('--disable-gpu')
        options.set_argument('--window-size=1920,1080')
        
        # User agent
        options.set_user_agent(
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Proxy
        if self.proxy_url:
            options.set_proxy(self.proxy_url)
        
        return ChromiumPage(options)
    
    async def scrape_site(
        self,
        url: str,
        timeout: int = 15
    ) -> Dict[str, Any]:
        """
        סריקת אתר וחילוץ מידע
        
        Args:
            url: כתובת האתר
            timeout: timeout בשניות
        
        Returns:
            {
                "inner_text": "תוכן האתר...",
                "emails": ["info@site.com"],
                "phones": ["03-1234567"],
                "title": "כותרת האתר",
                "meta_description": "תיאור...",
                "html": "HTML מלא (אם נדרש)"
            }
        """
        logger.info(f"Scraping: {url}")
        
        page = self._get_page()
        
        try:
            # ניווט לאתר
            page.get(url, timeout=timeout)
            
            # המתנה לטעינה
            page.wait.load_start()
            
            # חילוץ מידע
            result = {
                "url": url,
                "title": page.title,
                "inner_text": self._get_inner_text(page),
                "meta_description": self._get_meta_description(page),
                "emails": self._extract_emails(page.html),
                "phones": self._extract_phones(page.html),
                "html": page.html[:50000] if page.html else ""  # חיתוך HTML
            }
            
            logger.info(f"Scraped {url}: {len(result['inner_text'])} chars, "
                       f"{len(result['emails'])} emails, {len(result['phones'])} phones")
            
            return result
            
        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "inner_text": "",
                "emails": [],
                "phones": []
            }
            
        finally:
            page.quit()
    
    async def scrape_multiple(
        self,
        urls: List[str],
        delay_between: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        סריקת מספר אתרים
        """
        import asyncio
        
        results = []
        
        for url in urls:
            try:
                result = await self.scrape_site(url)
                results.append(result)
            except Exception as e:
                results.append({"url": url, "error": str(e)})
            
            # המתנה בין בקשות
            await asyncio.sleep(delay_between)
        
        return results
    
    def _get_inner_text(self, page) -> str:
        """חילוץ טקסט מהעמוד"""
        try:
            body = page.ele('body')
            if body:
                text = body.text
                # ניקוי טקסט
                text = re.sub(r'\s+', ' ', text)
                return text[:10000]  # חיתוך ל-10K
            return ""
        except:
            return ""
    
    def _get_meta_description(self, page) -> str:
        """חילוץ meta description"""
        try:
            meta = page.ele('meta[name="description"]')
            if meta:
                return meta.attr('content') or ""
            return ""
        except:
            return ""
    
    def _extract_emails(self, html: str) -> List[str]:
        """חילוץ כתובות מייל"""
        if not html:
            return []
        
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, html)
        
        # סינון
        filtered = []
        ignore_patterns = ['example.com', 'domain.com', 'email.com', 'test.com', 'wix', 'wordpress']
        
        for email in set(emails):
            email_lower = email.lower()
            if not any(p in email_lower for p in ignore_patterns):
                filtered.append(email)
        
        return filtered[:5]  # מקסימום 5 מיילים
    
    def _extract_phones(self, html: str) -> List[str]:
        """חילוץ מספרי טלפון"""
        if not html:
            return []
        
        patterns = [
            r'0[23489]-?\d{7}',            # טלפון קווי
            r'05[0-9]-?\d{7}',              # סלולרי
            r'\+972-?[235][0-9]?-?\d{7}',   # בינלאומי
            r'1-?800-?\d{6}',               # חיוג חינם
            r'\*\d{4}',                      # קיצור
        ]
        
        phones = []
        for pattern in patterns:
            found = re.findall(pattern, html)
            phones.extend(found)
        
        # נרמול והסרת כפילויות
        normalized = []
        for phone in phones:
            clean = re.sub(r'[^0-9+*]', '', phone)
            if clean not in normalized:
                normalized.append(clean)
        
        return normalized[:5]  # מקסימום 5 טלפונים


class SiteAnalyzer:
    """
    ניתוח אתר לזיהוי סוג העסק ורלוונטיות
    """
    
    def __init__(self):
        self.scraper = StealthScraper()
    
    async def analyze(self, url: str) -> Dict[str, Any]:
        """
        ניתוח מלא של אתר
        
        Returns:
            {
                "url": "...",
                "domain": "...",
                "scraped_data": {...},
                "is_accessible": True/False,
                "has_contact_info": True/False
            }
        """
        from urllib.parse import urlparse
        
        # חילוץ דומיין
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        
        # סריקה
        scraped = await self.scraper.scrape_site(url)
        
        return {
            "url": url,
            "domain": domain,
            "scraped_data": scraped,
            "is_accessible": "error" not in scraped,
            "has_contact_info": bool(scraped.get("emails") or scraped.get("phones")),
            "title": scraped.get("title", ""),
            "content_length": len(scraped.get("inner_text", ""))
        }


# Factory functions
def get_stealth_scraper(proxy_url: str = None) -> StealthScraper:
    """קבלת instance של StealthScraper"""
    return StealthScraper(proxy_url=proxy_url)


def get_site_analyzer() -> SiteAnalyzer:
    """קבלת instance של SiteAnalyzer"""
    return SiteAnalyzer()
