"""
PartnerCalc OS - ZenRows Scraper
סריקת תוכן עם ZenRows בלבד (פשוט ויעיל)
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings


class ZenRowsScraper:
    """
    סורק פשוט עם ZenRows בלבד
    ללא fallbacks - ZenRows עובד על כל האתרים
    """
    
    # ZenRows API key (can be overridden in settings)
    DEFAULT_API_KEY = "293560d128bbd0f2fdf5748fe3df4ba3b99327e2"
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, 'zenrows_api_key', None) or self.DEFAULT_API_KEY
    
    async def scrape(self, url: str) -> Dict[str, Any]:
        """
        סריקת URL עם ZenRows
        
        Args:
            url: URL to scrape
            
        Returns:
            {
                "url": "...",
                "title": "...",
                "meta_description": "...",
                "meta_keywords": "...",
                "nav_links": [...],
                "has_menu_calculator": True/False,
                "html": "...",
                "inner_text": "...",
                "emails": [...],
                "phones": [...],
                "method": "zenrows",
                "error": None
            }
        """
        import httpx
        
        logger.info(f"🌐 Scraping with ZenRows: {url}")
        
        try:
            # ZenRows API with Israeli proxy
            api_url = "https://api.zenrows.com/v1/"
            params = {
                "apikey": self.api_key,
                "url": url,
                "js_render": "true",       # Render JavaScript
                "antibot": "true",         # Anti-bot bypass
                "premium_proxy": "true",   # Premium proxies
                "proxy_country": "il"      # 🇮🇱 Israeli proxy
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(api_url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"ZenRows returned {response.status_code}: {response.text[:200]}")
                    return {
                        "url": url,
                        "error": f"ZenRows error: {response.status_code}",
                        "html": "",
                        "inner_text": "",
                        "emails": [],
                        "phones": [],
                        "method": "zenrows_failed"
                    }
                
                html = response.text
                logger.info(f"✅ ZenRows success: {len(html)} chars")
                return self._parse_html(url, html)
                
        except Exception as e:
            logger.error(f"ZenRows failed for {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "html": "",
                "inner_text": "",
                "emails": [],
                "phones": [],
                "method": "zenrows_failed"
            }
    
    def _parse_html(self, url: str, html: str) -> Dict[str, Any]:
        """פרסור HTML וחילוץ מידע"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title = ""
        if soup.title:
            title = soup.title.string or ""
        
        # Extract meta description
        meta_desc = ""
        meta = soup.find('meta', attrs={'name': 'description'})
        if meta:
            meta_desc = meta.get('content', '')
        
        # Extract meta keywords
        meta_keywords = ""
        meta_kw = soup.find('meta', attrs={'name': 'keywords'})
        if meta_kw:
            meta_keywords = meta_kw.get('content', '')
        
        # Extract navigation links
        nav_links = []
        calculator_keywords = ['מחשבון', 'calculator', 'חישוב', 'calc']
        has_menu_calculator = False
        
        for nav_element in soup.find_all(['nav', 'header']):
            for link in nav_element.find_all('a'):
                text = link.get_text(strip=True)
                href = link.get('href', '')
                if text and len(text) < 100:  # Reasonable menu item length
                    nav_links.append({"text": text, "href": href})
                    # Check if calculator in menu
                    if any(kw in text.lower() for kw in calculator_keywords):
                        has_menu_calculator = True
        
        # Extract inner text
        inner_text = ""
        if soup.body:
            # Remove script and style elements
            for element in soup.body(['script', 'style', 'noscript']):
                element.decompose()
            inner_text = soup.body.get_text(separator=' ', strip=True)[:15000]
        
        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "meta_keywords": meta_keywords,
            "nav_links": nav_links,
            "has_menu_calculator": has_menu_calculator,
            "html": html[:50000],
            "inner_text": inner_text,
            "emails": self._extract_emails(html),
            "phones": self._extract_phones(html),
            "method": "zenrows",
            "error": None
        }
    
    def _extract_emails(self, html: str) -> List[str]:
        """חילוץ אימיילים"""
        if not html:
            return []
        
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, html)
        
        ignore = ['example.com', 'domain.com', 'email.com', 'test.com',
                  'wix', 'wordpress', 'sentry', 'google', 'facebook',
                  'schema.org', 'w3.org', 'cloudflare']
        
        filtered = []
        for email in set(emails):
            email_lower = email.lower()
            if not any(p in email_lower for p in ignore):
                if len(email) < 50:  # Filter out garbage
                    filtered.append(email)
        
        return filtered[:5]
    
    def _extract_phones(self, html: str) -> List[str]:
        """חילוץ טלפונים ישראליים"""
        if not html:
            return []
        
        patterns = [
            r'0[23489]-?\d{7}',
            r'05[0-9]-?\d{7}',
            r'\+972-?[235][0-9]?-?\d{7}',
            r'1-?800-?\d{6}',
            r'\*\d{4}',
        ]
        
        phones = []
        for pattern in patterns:
            phones.extend(re.findall(pattern, html))
        
        normalized = []
        for phone in phones:
            clean = re.sub(r'[^0-9+*]', '', phone)
            if clean not in normalized and len(clean) >= 4:
                normalized.append(clean)
        
        return normalized[:5]
    
    async def scrape_batch(
        self,
        urls: List[str],
        delay: float = 0.5,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        סריקת מספר URLs במקביל
        """
        import asyncio
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(url: str) -> Dict[str, Any]:
            async with semaphore:
                result = await self.scrape(url)
                await asyncio.sleep(delay)
                return result
        
        tasks = [scrape_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    "url": urls[i],
                    "error": str(result),
                    "html": "",
                    "inner_text": "",
                    "emails": [],
                    "phones": [],
                    "method": "zenrows_failed"
                })
            else:
                final_results.append(result)
        
        return final_results


# Singleton
_zenrows_scraper: Optional[ZenRowsScraper] = None


def get_zenrows_scraper() -> ZenRowsScraper:
    """קבלת instance של ZenRowsScraper"""
    global _zenrows_scraper
    if _zenrows_scraper is None:
        _zenrows_scraper = ZenRowsScraper()
    return _zenrows_scraper


# Backward compatibility - keep old function name
def get_smart_scraper() -> ZenRowsScraper:
    """Backward compatibility wrapper"""
    return get_zenrows_scraper()
