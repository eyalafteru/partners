"""
PartnerCalc OS - Deep Scraper
סריקה מעמיקה של אתרים - סורק 10-20 עמודים פנימיים
"""
import asyncio
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from urllib.parse import urljoin, urlparse
from loguru import logger

from app.scraper.smart_scraper import get_smart_scraper


class DeepScraper:
    """
    סורק מעמיק - סורק עמודים פנימיים של אתר
    """
    
    # עמודים חשובים לסריקה (נתיבים נפוצים)
    IMPORTANT_PATHS = [
        "/", 
        "/about", "/about-us", "/aboutus", "/אודות", "/אודותינו",
        "/services", "/our-services", "/שירותים",
        "/contact", "/contact-us", "/contactus", "/צור-קשר", "/יצירת-קשר",
        "/products", "/מוצרים",
        "/pricing", "/prices", "/מחירים", "/תעריפים",
        "/blog", "/בלוג", "/articles", "/מאמרים",
        "/faq", "/שאלות-נפוצות",
        "/team", "/הצוות", "/our-team",
        "/portfolio", "/projects", "/פרויקטים",
        "/testimonials", "/לקוחות-ממליצים",
    ]
    
    # סוגי עמודים לזיהוי
    PAGE_TYPE_PATTERNS = {
        "home": ["/", "/home", "/index"],
        "about": ["/about", "/אודות", "/who-we-are"],
        "services": ["/services", "/שירותים", "/what-we-do"],
        "contact": ["/contact", "/צור-קשר", "/reach-us"],
        "pricing": ["/pricing", "/prices", "/מחירים", "/תעריפים"],
        "blog": ["/blog", "/בלוג", "/articles", "/news"],
        "products": ["/products", "/מוצרים", "/shop"],
        "faq": ["/faq", "/שאלות"],
        "team": ["/team", "/הצוות", "/about-us"],
    }
    
    def __init__(self, max_pages: int = 15):
        self.scraper = get_smart_scraper()
        self.max_pages = max_pages
    
    def _detect_page_type(self, path: str) -> str:
        """זיהוי סוג העמוד לפי הנתיב"""
        path_lower = path.lower()
        
        for page_type, patterns in self.PAGE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in path_lower:
                    return page_type
        
        return "other"
    
    def _extract_internal_links(self, html: str, base_url: str) -> Set[str]:
        """חילוץ קישורים פנימיים מ-HTML"""
        links = set()
        
        # Extract href values
        href_pattern = r'href=["\']([^"\']+)["\']'
        matches = re.findall(href_pattern, html, re.IGNORECASE)
        
        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc.replace("www.", "")
        
        for href in matches:
            try:
                # Skip anchors, javascript, mailto, tel
                if href.startswith("#") or href.startswith("javascript:") or \
                   href.startswith("mailto:") or href.startswith("tel:"):
                    continue
                
                # Make absolute URL
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                
                # Check if internal link
                link_domain = parsed.netloc.replace("www.", "")
                if link_domain == base_domain:
                    # Clean URL (remove query and fragment)
                    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    links.add(clean_url)
                    
            except Exception:
                continue
        
        return links
    
    def _has_contact_form(self, html: str) -> tuple:
        """בדיקה אם יש טופס יצירת קשר"""
        form_patterns = [
            r'<form[^>]*(?:contact|message|inquiry|צור.?קשר|שלח.?הודעה)[^>]*>',
            r'<form[^>]*action=["\'][^"\']*(?:contact|message|send)[^"\']*["\'][^>]*>',
            r'<input[^>]*name=["\'](?:email|message|phone|name)["\'][^>]*>.*<button',
        ]
        
        for pattern in form_patterns:
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                # Try to extract form HTML
                form_match = re.search(r'<form[^>]*>.*?</form>', html, re.IGNORECASE | re.DOTALL)
                if form_match:
                    return True, form_match.group()[:5000]
        
        return False, None
    
    async def scrape_page(self, url: str) -> Dict[str, Any]:
        """סריקת עמוד בודד"""
        try:
            result = await self.scraper.scrape(url)
            
            if not result or result.get("error"):
                return {
                    "url": url,
                    "success": False,
                    "error": result.get("error", "Failed to scrape")
                }
            
            html = result.get("html", "")
            has_form, form_html = self._has_contact_form(html)
            
            return {
                "url": url,
                "path": urlparse(url).path or "/",
                "title": result.get("title", ""),
                "html_text": result.get("inner_text", "")[:10000],
                "html": html,
                "has_contact_form": has_form,
                "form_html": form_html,
                "internal_links": self._extract_internal_links(html, url),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": str(e)
            }
    
    async def deep_scan(self, base_url: str) -> Dict[str, Any]:
        """
        סריקה מעמיקה של אתר
        
        1. סורק דף הבית
        2. מחלץ קישורים פנימיים
        3. סורק עמודים חשובים
        4. מחזיר את כל העמודים הסרוקים
        """
        logger.info(f"🔍 Starting deep scan: {base_url}")
        
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        scanned_pages = []
        scanned_urls = set()
        
        # Step 1: Scan home page first
        home_result = await self.scrape_page(base_url)
        if home_result["success"]:
            home_result["page_type"] = "home"
            scanned_pages.append(home_result)
            scanned_urls.add(base_url)
            
            # Get internal links from home
            internal_links = home_result.get("internal_links", set())
        else:
            return {
                "base_url": base_url,
                "pages": [],
                "total_pages": 0,
                "success": False,
                "error": home_result.get("error")
            }
        
        # Step 2: Try important paths
        urls_to_scan = []
        
        for path in self.IMPORTANT_PATHS:
            url = urljoin(domain, path)
            if url not in scanned_urls:
                urls_to_scan.append(url)
        
        # Add discovered internal links
        for link in internal_links:
            if link not in scanned_urls and link not in urls_to_scan:
                # Prioritize links that look like important pages
                path = urlparse(link).path.lower()
                if any(imp in path for imp in ["about", "contact", "service", "price", "אודות", "קשר", "שירות"]):
                    urls_to_scan.insert(0, link)
                else:
                    urls_to_scan.append(link)
        
        # Step 3: Scan additional pages (up to max_pages)
        remaining = self.max_pages - 1  # Already scanned home
        
        for url in urls_to_scan[:remaining * 2]:  # Try more URLs in case some fail
            if len(scanned_pages) >= self.max_pages:
                break
                
            if url in scanned_urls:
                continue
            
            logger.debug(f"  Scanning: {url}")
            result = await self.scrape_page(url)
            
            if result["success"]:
                result["page_type"] = self._detect_page_type(result.get("path", ""))
                scanned_pages.append(result)
                scanned_urls.add(url)
            
            # Small delay
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Deep scan complete: {len(scanned_pages)} pages from {base_url}")
        
        return {
            "base_url": base_url,
            "domain": parsed.netloc,
            "pages": scanned_pages,
            "total_pages": len(scanned_pages),
            "has_contact_form": any(p.get("has_contact_form") for p in scanned_pages),
            "page_types": list(set(p.get("page_type") for p in scanned_pages)),
            "success": True
        }
    
    def summarize_content(self, pages: List[Dict]) -> str:
        """
        יצירת סיכום תוכן מכל העמודים הסרוקים
        """
        summary_parts = []
        
        for page in pages:
            if page.get("html_text"):
                page_type = page.get("page_type", "other")
                title = page.get("title", "")
                content = page.get("html_text", "")[:2000]
                
                summary_parts.append(f"=== {page_type.upper()} ({title}) ===\n{content}")
        
        return "\n\n".join(summary_parts)[:8000]


# Singleton
_deep_scraper: Optional[DeepScraper] = None


def get_deep_scraper(max_pages: int = 15) -> DeepScraper:
    """קבלת instance של DeepScraper"""
    global _deep_scraper
    if _deep_scraper is None:
        _deep_scraper = DeepScraper(max_pages)
    return _deep_scraper
