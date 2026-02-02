"""
PartnerCalc OS - Apify Client
סריקת תוצאות גוגל דרך Apify
"""
from typing import List, Dict, Any, Optional
from loguru import logger
from urllib.parse import urlparse

from app.config import settings


class ApifyGoogleScraper:
    """
    Client לסריקת תוצאות גוגל דרך Apify
    Actor: nFJndFXA5zjCTuudP (Google Search Results Scraper)
    """
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token or settings.apify_token
        self.actor_id = "nFJndFXA5zjCTuudP"
    
    async def search(
        self,
        query: str,
        max_results: int = 100,
        country: str = "il",
        language: str = "iw"  # Hebrew language code (old ISO code used by Google)
    ) -> List[Dict[str, Any]]:
        """
        חיפוש בגוגל וקבלת תוצאות
        
        Args:
            query: מילות חיפוש
            max_results: כמות תוצאות (50, 100, 150, 200)
            country: קוד מדינה
            language: קוד שפה
        
        Returns:
            רשימת תוצאות:
            [
                {
                    "url": "https://example.com",
                    "title": "כותרת",
                    "description": "תיאור",
                    "position": 1
                }
            ]
        """
        from apify_client import ApifyClient
        
        logger.info(f"Searching Google: '{query}' ({max_results} results)")
        
        client = ApifyClient(self.api_token)
        
        # הגדרות הריצה
        run_input = {
            "queries": query,
            "maxPagesPerQuery": max_results // 10,  # 10 תוצאות לעמוד
            "resultsPerPage": 10,
            "countryCode": country,
            "languageCode": language,
            "mobileResults": False,
            "includeUnfilteredResults": False,
            "saveHtml": False,
            "saveHtmlToKeyValueStore": False,
        }
        
        try:
            # הרצת ה-Actor
            run = client.actor(self.actor_id).call(run_input=run_input)
            
            # שליפת התוצאות
            results = []
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                organic_results = item.get("organicResults", [])
                
                for result in organic_results:
                    results.append({
                        "url": result.get("url"),
                        "title": result.get("title"),
                        "description": result.get("description"),
                        "position": result.get("position"),
                        "domain": self._extract_domain(result.get("url", ""))
                    })
            
            logger.info(f"Found {len(results)} results for '{query}'")
            return results
            
        except Exception as e:
            logger.error(f"Apify search failed: {e}")
            raise
    
    async def search_multiple(
        self,
        queries: List[str],
        max_results_per_query: int = 100,
        deduplicate: bool = True
    ) -> List[Dict[str, Any]]:
        """
        חיפוש מרובה שאילתות עם סינון כפילויות
        
        Args:
            queries: רשימת שאילתות
            max_results_per_query: תוצאות לכל שאילתה
            deduplicate: סינון כפילויות לפי דומיין
        
        Returns:
            רשימת תוצאות (ייחודיות)
        """
        all_results = []
        
        for query in queries:
            try:
                results = await self.search(query, max_results_per_query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to search '{query}': {e}")
        
        if deduplicate:
            # סינון כפילויות לפי דומיין
            seen_domains = set()
            unique_results = []
            
            for result in all_results:
                domain = result.get("domain", "")
                if domain and domain not in seen_domains:
                    seen_domains.add(domain)
                    unique_results.append(result)
            
            duplicates_removed = len(all_results) - len(unique_results)
            logger.info(f"Removed {duplicates_removed} duplicates, {len(unique_results)} unique domains")
            
            return unique_results
        
        return all_results
    
    def _extract_domain(self, url: str) -> str:
        """חילוץ דומיין מ-URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            
            # הסרת www.
            if domain.startswith("www."):
                domain = domain[4:]
            
            return domain
        except:
            return ""
    
    async def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """קבלת סטטוס ריצה"""
        from apify_client import ApifyClient
        
        client = ApifyClient(self.api_token)
        run = client.run(run_id).get()
        
        return {
            "status": run.get("status"),
            "started_at": run.get("startedAt"),
            "finished_at": run.get("finishedAt"),
            "usage": run.get("usage")
        }


# Singleton
_apify_scraper: Optional[ApifyGoogleScraper] = None


def get_apify_scraper() -> ApifyGoogleScraper:
    """קבלת instance של Apify scraper"""
    global _apify_scraper
    if _apify_scraper is None:
        _apify_scraper = ApifyGoogleScraper()
    return _apify_scraper
