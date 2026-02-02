"""
PartnerCalc OS - Smart Scraper
סריקה חכמה עם fallbacks:
1. httpx פשוט (מהיר, חינם)
2. DrissionPage דפדפן מקומי (עוקף JS)
3. Zenrows (עוקף CloudFlare)
"""
import re
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger
from urllib.parse import urlparse

from app.config import settings


class SmartScraper:
    """
    סורק חכם עם אסטרטגיית fallback
    """
    
    # Zenrows API key
    ZENROWS_API_KEY = "293560d128bbd0f2fdf5748fe3df4ba3b99327e2"
    
    # User agents לרוטציה
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    
    def __init__(self):
        self.session = None
        self._user_agent_index = 0
    
    def _get_user_agent(self) -> str:
        """רוטציית User Agent"""
        ua = self.USER_AGENTS[self._user_agent_index % len(self.USER_AGENTS)]
        self._user_agent_index += 1
        return ua
    
    async def scrape(self, url: str, force_browser: bool = False) -> Dict[str, Any]:
        """
        סריקה חכמה עם fallbacks
        
        נסיון 1: httpx פשוט (מדולג אם force_browser=True)
        נסיון 2: DrissionPage (דפדפן מקומי)
        נסיון 3: Zenrows (עקיפת CloudFlare)
        
        Args:
            url: URL to scrape
            force_browser: If True, skip httpx and start with DrissionPage (for JS sites)
        """
        logger.info(f"Smart scraping: {url} (force_browser={force_browser})")
        
        # For loan-israel.co.il - use Zenrows first (JS rendering needed)
        if "loan-israel.co.il" in url:
            logger.info(f"loan-israel.co.il detected - using Zenrows with JS rendering")
            result = await self._try_zenrows(url)
            if result:
                logger.info(f"✓ Zenrows succeeded for {url}")
                return result
        
        # נסיון 1: httpx פשוט (מדולג אם force_browser=True)
        if not force_browser:
            result = await self._try_httpx(url)
            if result and not result.get("blocked"):
                logger.info(f"✓ httpx succeeded for {url}")
                return result
            logger.info(f"httpx blocked/failed, trying DrissionPage...")
        else:
            logger.info(f"force_browser=True, skipping httpx, starting with DrissionPage...")
        
        # נסיון 2: DrissionPage
        result = await self._try_drission(url)
        if result and not result.get("blocked"):
            logger.info(f"✓ DrissionPage succeeded for {url}")
            return result
        
        logger.info(f"DrissionPage blocked/failed, trying Zenrows...")
        
        # נסיון 3: Zenrows
        result = await self._try_zenrows(url)
        if result:
            logger.info(f"✓ Zenrows succeeded for {url}")
            return result
        
        logger.error(f"All methods failed for {url}")
        return {
            "url": url,
            "error": "All scraping methods failed",
            "html": "",
            "inner_text": "",
            "emails": [],
            "phones": [],
            "method": "failed"
        }
    
    async def _try_httpx(self, url: str) -> Optional[Dict[str, Any]]:
        """נסיון סריקה עם httpx"""
        import httpx
        
        try:
            headers = {
                "User-Agent": self._get_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                verify=False
            ) as client:
                response = await client.get(url, headers=headers)
                
                # Check for blocks
                if response.status_code in [403, 503, 429]:
                    return {"blocked": True, "status": response.status_code}
                
                if response.status_code != 200:
                    return None
                
                html = response.text
                
                # Check for CloudFlare challenge
                if self._is_cloudflare_challenge(html):
                    return {"blocked": True, "reason": "cloudflare"}
                
                return self._parse_html(url, html, "httpx")
                
        except Exception as e:
            logger.debug(f"httpx failed for {url}: {e}")
            return None
    
    async def _try_drission(self, url: str) -> Optional[Dict[str, Any]]:
        """נסיון סריקה עם DrissionPage (דפדפן מקומי)"""
        try:
            from DrissionPage import ChromiumPage, ChromiumOptions
            
            options = ChromiumOptions()
            options.headless(True)
            options.set_argument('--disable-blink-features=AutomationControlled')
            options.set_argument('--no-sandbox')
            options.set_argument('--disable-dev-shm-usage')
            options.set_argument('--disable-gpu')
            options.set_argument('--window-size=1920,1080')
            options.set_user_agent(self._get_user_agent())
            
            page = ChromiumPage(options)
            
            try:
                page.get(url, timeout=20)
                page.wait.load_start()
                
                # Wait a bit for JS to execute
                await asyncio.sleep(2)
                
                html = page.html
                
                # Check for CloudFlare
                if self._is_cloudflare_challenge(html):
                    return {"blocked": True, "reason": "cloudflare"}
                
                inner_text = ""
                try:
                    body = page.ele('body')
                    if body:
                        inner_text = body.text[:15000]
                except:
                    pass
                
                result = self._parse_html(url, html, "drission")
                result["inner_text"] = inner_text
                return result
                
            finally:
                page.quit()
                
        except Exception as e:
            logger.debug(f"DrissionPage failed for {url}: {e}")
            return None
    
    async def _try_zenrows(self, url: str) -> Optional[Dict[str, Any]]:
        """נסיון סריקה עם Zenrows (עקיפת CloudFlare + פרוקסי ישראלי)"""
        import httpx
        
        try:
            # Zenrows API with Israeli proxy
            api_url = "https://api.zenrows.com/v1/"
            params = {
                "apikey": self.ZENROWS_API_KEY,
                "url": url,
                "js_render": "true",       # Render JavaScript
                "antibot": "true",         # Anti-bot bypass
                "premium_proxy": "true",   # Premium proxies
                "proxy_country": "il"      # 🇮🇱 Israeli proxy
            }
            
            logger.info(f"🌐 Zenrows request with IL proxy: {url}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(api_url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Zenrows returned {response.status_code}: {response.text[:200]}")
                    return None
                
                html = response.text
                logger.info(f"✅ Zenrows success: {len(html)} chars")
                return self._parse_html(url, html, "zenrows")
                
        except Exception as e:
            logger.error(f"Zenrows failed for {url}: {e}")
            return None
    
    def _is_cloudflare_challenge(self, html: str) -> bool:
        """בדיקה אם יש אתגר CloudFlare"""
        if not html:
            return False
        
        cf_indicators = [
            "cf-browser-verification",
            "cf_clearance",
            "Checking your browser",
            "Just a moment...",
            "DDoS protection by Cloudflare",
            "Please Wait... | Cloudflare",
            "__cf_bm",
            "challenge-platform"
        ]
        
        return any(indicator in html for indicator in cf_indicators)
    
    def _parse_html(self, url: str, html: str, method: str) -> Dict[str, Any]:
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
            "method": method,
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
    
    async def scrape_with_zenrows_first(self, url: str) -> Dict[str, Any]:
        """
        סריקה עם ZenRows כברירת מחדל (לאתרים עם JS כבד)
        Fallback ל-DrissionPage אם ZenRows נכשל
        """
        logger.info(f"🌐 Scraping with ZenRows first: {url}")
        
        # נסיון 1: ZenRows (הכי חזק)
        result = await self._try_zenrows(url)
        if result and result.get("inner_text") and len(result.get("inner_text", "")) >= 100:
            logger.info(f"✅ ZenRows succeeded for {url}: {len(result.get('inner_text', ''))} chars")
            return result
        
        logger.info(f"⚠️ ZenRows returned short content, trying DrissionPage...")
        
        # נסיון 2: DrissionPage
        result = await self._try_drission(url)
        if result and result.get("inner_text") and len(result.get("inner_text", "")) >= 100:
            logger.info(f"✅ DrissionPage succeeded for {url}: {len(result.get('inner_text', ''))} chars")
            return result
        
        logger.warning(f"❌ All methods returned short content for {url}")
        return result or {
            "url": url,
            "error": "Content too short from all methods",
            "html": "",
            "inner_text": "",
            "emails": [],
            "phones": [],
            "method": "failed"
        }

    async def scrape_batch(
        self,
        urls: List[str],
        delay: float = 1.0,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        סריקת מספר URLs עם rate limiting
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
                    "phones": []
                })
            else:
                final_results.append(result)
        
        return final_results


# Singleton
_smart_scraper: Optional[SmartScraper] = None


def get_smart_scraper() -> SmartScraper:
    """קבלת instance של SmartScraper"""
    global _smart_scraper
    if _smart_scraper is None:
        _smart_scraper = SmartScraper()
    return _smart_scraper
