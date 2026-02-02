"""
PartnerCalc OS - Apify HTML Scraper
סריקת HTML עם עקיפת CloudFlare דרך Apify
"""
import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.config import settings


class ApifyHtmlScraper:
    """
    סורק HTML דרך Apify Web Scraper
    עוקף CloudFlare ובוטים אחרים
    """
    
    # Apify Web Scraper Actor
    WEB_SCRAPER_ACTOR = "apify/web-scraper"
    # Cheerio Scraper - יותר מהיר לדפים פשוטים
    CHEERIO_ACTOR = "apify/cheerio-scraper"
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token or settings.apify_token
    
    async def scrape_url(
        self,
        url: str,
        use_browser: bool = True,
        timeout_secs: int = 60
    ) -> Dict[str, Any]:
        """
        סריקת URL בודד
        
        Args:
            url: כתובת לסריקה
            use_browser: True = Puppeteer (עוקף CF), False = Cheerio (מהיר)
            timeout_secs: timeout בשניות
        
        Returns:
            {
                "url": "...",
                "html": "...",
                "title": "...",
                "inner_text": "...",
                "emails": [...],
                "phones": [...],
                "error": None or "..."
            }
        """
        from apify_client import ApifyClient
        
        logger.info(f"Apify scraping: {url} (browser={use_browser})")
        
        client = ApifyClient(self.api_token)
        
        if use_browser:
            # Web Scraper with Puppeteer - bypasses CloudFlare
            run_input = {
                "startUrls": [{"url": url}],
                "pageFunction": """
                    async function pageFunction(context) {
                        const { page, request } = context;
                        
                        // Wait for page to load
                        await page.waitForSelector('body', { timeout: 10000 }).catch(() => {});
                        
                        // Get page content
                        const title = await page.title();
                        const html = await page.content();
                        const text = await page.evaluate(() => document.body.innerText);
                        
                        return {
                            url: request.url,
                            title,
                            html,
                            innerText: text.substring(0, 15000)
                        };
                    }
                """,
                "proxyConfiguration": {"useApifyProxy": True},
                "maxRequestsPerCrawl": 1,
                "maxConcurrency": 1,
            }
            actor_id = self.WEB_SCRAPER_ACTOR
        else:
            # Cheerio Scraper - faster for simple pages
            run_input = {
                "startUrls": [{"url": url}],
                "pageFunction": """
                    async function pageFunction(context) {
                        const { $, request } = context;
                        
                        return {
                            url: request.url,
                            title: $('title').text(),
                            html: $.html(),
                            innerText: $('body').text().substring(0, 15000)
                        };
                    }
                """,
                "proxyConfiguration": {"useApifyProxy": True},
                "maxRequestsPerCrawl": 1,
            }
            actor_id = self.CHEERIO_ACTOR
        
        try:
            # Run the actor
            run = client.actor(actor_id).call(
                run_input=run_input,
                timeout_secs=timeout_secs
            )
            
            # Get results
            items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            
            if items:
                item = items[0]
                html = item.get("html", "")
                
                result = {
                    "url": url,
                    "title": item.get("title", ""),
                    "html": html[:50000],  # Limit HTML size
                    "inner_text": item.get("innerText", "")[:15000],
                    "emails": self._extract_emails(html),
                    "phones": self._extract_phones(html),
                    "error": None
                }
                
                logger.info(f"Scraped {url}: {len(result['inner_text'])} chars, "
                           f"{len(result['emails'])} emails")
                return result
            else:
                return {
                    "url": url,
                    "error": "No data returned",
                    "html": "",
                    "inner_text": "",
                    "emails": [],
                    "phones": []
                }
                
        except Exception as e:
            logger.error(f"Apify scrape failed for {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "html": "",
                "inner_text": "",
                "emails": [],
                "phones": []
            }
    
    async def scrape_batch(
        self,
        urls: List[str],
        use_browser: bool = True,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        סריקת מספר URLs בבת אחת
        חוסך זמן וכסף לעומת סריקה בודדת
        """
        from apify_client import ApifyClient
        
        logger.info(f"Batch scraping {len(urls)} URLs")
        
        client = ApifyClient(self.api_token)
        
        start_urls = [{"url": url} for url in urls]
        
        if use_browser:
            run_input = {
                "startUrls": start_urls,
                "pageFunction": """
                    async function pageFunction(context) {
                        const { page, request } = context;
                        
                        await page.waitForSelector('body', { timeout: 10000 }).catch(() => {});
                        
                        const title = await page.title();
                        const html = await page.content();
                        const text = await page.evaluate(() => document.body.innerText);
                        
                        return {
                            url: request.url,
                            title,
                            html: html.substring(0, 50000),
                            innerText: text.substring(0, 15000)
                        };
                    }
                """,
                "proxyConfiguration": {"useApifyProxy": True},
                "maxRequestsPerCrawl": len(urls),
                "maxConcurrency": max_concurrent,
            }
            actor_id = self.WEB_SCRAPER_ACTOR
        else:
            run_input = {
                "startUrls": start_urls,
                "pageFunction": """
                    async function pageFunction(context) {
                        const { $, request } = context;
                        
                        return {
                            url: request.url,
                            title: $('title').text(),
                            html: $.html().substring(0, 50000),
                            innerText: $('body').text().substring(0, 15000)
                        };
                    }
                """,
                "proxyConfiguration": {"useApifyProxy": True},
                "maxRequestsPerCrawl": len(urls),
                "maxConcurrency": max_concurrent,
            }
            actor_id = self.CHEERIO_ACTOR
        
        try:
            run = client.actor(actor_id).call(run_input=run_input)
            
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                html = item.get("html", "")
                results.append({
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "html": html,
                    "inner_text": item.get("innerText", ""),
                    "emails": self._extract_emails(html),
                    "phones": self._extract_phones(html),
                    "error": None
                })
            
            logger.info(f"Batch scraped {len(results)}/{len(urls)} URLs")
            return results
            
        except Exception as e:
            logger.error(f"Batch scrape failed: {e}")
            return [{"url": url, "error": str(e)} for url in urls]
    
    def _extract_emails(self, html: str) -> List[str]:
        """חילוץ כתובות מייל"""
        if not html:
            return []
        
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(pattern, html)
        
        # סינון ספאם
        ignore = ['example.com', 'domain.com', 'email.com', 'test.com', 
                  'wix', 'wordpress', 'sentry', 'google', 'facebook']
        
        filtered = []
        for email in set(emails):
            email_lower = email.lower()
            if not any(p in email_lower for p in ignore):
                filtered.append(email)
        
        return filtered[:5]
    
    def _extract_phones(self, html: str) -> List[str]:
        """חילוץ מספרי טלפון ישראליים"""
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
        
        # נרמול
        normalized = []
        for phone in phones:
            clean = re.sub(r'[^0-9+*]', '', phone)
            if clean not in normalized:
                normalized.append(clean)
        
        return normalized[:5]


# Singleton
_apify_html_scraper: Optional[ApifyHtmlScraper] = None


def get_apify_html_scraper() -> ApifyHtmlScraper:
    """קבלת instance של ApifyHtmlScraper"""
    global _apify_html_scraper
    if _apify_html_scraper is None:
        _apify_html_scraper = ApifyHtmlScraper()
    return _apify_html_scraper
