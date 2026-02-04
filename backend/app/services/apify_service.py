"""
PartnerCalc OS - Apify Integration Service
שירות לאינטגרציה עם Apify לפייסבוק
"""
import httpx
import asyncio
import json
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings


class ApifyService:
    """שירות אינטגרציה עם Apify"""
    
    def __init__(self):
        self.api_token = settings.apify_token
        self.base_url = "https://api.apify.com/v2"
        
        # Actor IDs
        self.fb_poster_actor = settings.apify_fb_poster_actor
        self.fb_comments_actor = settings.apify_fb_comments_actor
        self.fb_messenger_actor = settings.apify_fb_messenger_actor
        self.fb_groups_scraper = settings.apify_fb_groups_scraper
        
        # Facebook cookie
        self.facebook_cookie = settings.facebook_cookie
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.api_token)
    
    @property
    def has_facebook_cookie(self) -> bool:
        """בדיקה אם יש Facebook cookie"""
        return bool(self.facebook_cookie)
    
    def _get_headers(self) -> Dict[str, str]:
        """הכנת headers לקריאות API"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def _parse_cookie(self) -> List[Dict[str, Any]]:
        """המרת cookie מ-string ל-list"""
        if not self.facebook_cookie:
            return []
        
        try:
            if isinstance(self.facebook_cookie, str):
                return json.loads(self.facebook_cookie)
            return self.facebook_cookie
        except:
            logger.error("Failed to parse Facebook cookie")
            return []
    
    async def run_actor(
        self,
        actor_id: str,
        input_data: Dict[str, Any],
        wait_for_finish: bool = False,
        timeout_secs: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        הרצת Actor ב-Apify
        
        Args:
            actor_id: מזהה ה-Actor
            input_data: נתוני קלט
            wait_for_finish: האם להמתין לסיום
            timeout_secs: timeout בשניות
            
        Returns:
            dict עם run info, או None בשגיאה
        """
        if not self.is_configured:
            logger.warning("🎭 Apify not configured")
            return None
        
        try:
            url = f"{self.base_url}/acts/{actor_id}/runs"
            
            params = {"token": self.api_token}
            if wait_for_finish:
                params["waitForFinish"] = timeout_secs
            
            async with httpx.AsyncClient(timeout=timeout_secs + 30) as client:
                response = await client.post(
                    url,
                    params=params,
                    json=input_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    run_info = data.get("data", data)
                    logger.info(f"🎭 ✅ Actor {actor_id} started: {run_info.get('id')}")
                    return run_info
                else:
                    logger.error(f"🎭 ❌ Actor run failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"🎭 ❌ Apify error: {e}")
            return None
    
    async def get_run_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """
        קבלת סטטוס של run
        """
        if not self.is_configured:
            return None
        
        try:
            url = f"{self.base_url}/actor-runs/{run_id}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    url,
                    params={"token": self.api_token}
                )
                
                if response.status_code == 200:
                    return response.json().get("data", {})
                return None
                
        except Exception as e:
            logger.error(f"🎭 ❌ Get run status error: {e}")
            return None
    
    async def get_run_dataset(self, run_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        קבלת תוצאות dataset של run
        """
        if not self.is_configured:
            return None
        
        try:
            url = f"{self.base_url}/actor-runs/{run_id}/dataset/items"
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(
                    url,
                    params={"token": self.api_token}
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
                
        except Exception as e:
            logger.error(f"🎭 ❌ Get dataset error: {e}")
            return None
    
    # ========== Facebook Group Poster ==========
    
    async def post_to_groups(
        self,
        group_urls: List[str],
        messages: List[str],
        delay_seconds: int = 60
    ) -> Optional[Dict[str, Any]]:
        """
        פרסום לקבוצות פייסבוק
        
        Args:
            group_urls: רשימת URLs של קבוצות
            messages: רשימת הודעות (יבחר אקראית)
            delay_seconds: השהייה בין פוסטים
            
        Returns:
            run info
        """
        if not self.has_facebook_cookie:
            logger.error("🎭 ❌ Facebook cookie not configured")
            return None
        
        input_data = {
            "groupUrls": group_urls,
            "messages": messages,
            "delay": delay_seconds,
            "cookies": self._parse_cookie()
        }
        
        return await self.run_actor(
            actor_id=self.fb_poster_actor,
            input_data=input_data,
            wait_for_finish=False  # לא ממתינים - זה יכול לקחת זמן
        )
    
    async def post_single(
        self,
        group_url: str,
        message: str,
        wait_for_finish: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        פרסום פוסט בודד לקבוצה
        """
        return await self.post_to_groups(
            group_urls=[group_url],
            messages=[message],
            delay_seconds=0
        )
    
    # ========== Facebook Comments Scraper ==========
    
    async def scrape_post_comments(
        self,
        post_urls: List[str],
        max_comments: int = 100,
        sort_by: str = "newest"
    ) -> Optional[Dict[str, Any]]:
        """
        סריקת תגובות מפוסטים
        
        Args:
            post_urls: רשימת URLs של פוסטים
            max_comments: מקסימום תגובות לסרוק
            sort_by: מיון (newest, most_relevant)
            
        Returns:
            run info
        """
        input_data = {
            "startUrls": [{"url": url} for url in post_urls],
            "maxComments": max_comments,
            "sortBy": sort_by,
            "includeReplies": True
        }
        
        return await self.run_actor(
            actor_id=self.fb_comments_actor,
            input_data=input_data,
            wait_for_finish=True,
            timeout_secs=300
        )
    
    async def get_post_comments(
        self,
        post_url: str,
        max_comments: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        קבלת תגובות מפוסט ספציפי
        
        Returns:
            רשימת תגובות
        """
        run_info = await self.scrape_post_comments(
            post_urls=[post_url],
            max_comments=max_comments
        )
        
        if not run_info:
            return None
        
        run_id = run_info.get("id")
        if not run_id:
            return None
        
        # קבלת התוצאות
        return await self.get_run_dataset(run_id)
    
    # ========== Facebook Messenger ==========
    
    async def send_messenger_messages(
        self,
        profile_urls: List[str],
        message: str,
        delay_seconds: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        שליחת הודעות Messenger
        
        Args:
            profile_urls: רשימת URLs של פרופילים
            message: ההודעה לשליחה
            delay_seconds: השהייה בין הודעות
            
        Returns:
            run info
        """
        if not self.has_facebook_cookie:
            logger.error("🎭 ❌ Facebook cookie not configured")
            return None
        
        input_data = {
            "profileUrls": profile_urls,
            "message": message,
            "delay": delay_seconds,
            "cookies": self._parse_cookie()
        }
        
        return await self.run_actor(
            actor_id=self.fb_messenger_actor,
            input_data=input_data,
            wait_for_finish=False
        )
    
    async def send_single_message(
        self,
        profile_url: str,
        message: str
    ) -> Optional[Dict[str, Any]]:
        """
        שליחת הודעה לפרופיל בודד
        """
        return await self.send_messenger_messages(
            profile_urls=[profile_url],
            message=message,
            delay_seconds=0
        )
    
    # ========== Facebook Groups Scraper ==========
    
    async def search_groups(
        self,
        search_query: str,
        max_groups: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """
        חיפוש קבוצות פייסבוק
        
        Args:
            search_query: מחרוזת חיפוש
            max_groups: מקסימום קבוצות
            
        Returns:
            רשימת קבוצות
        """
        input_data = {
            "searchQuery": search_query,
            "maxGroups": max_groups
        }
        
        run_info = await self.run_actor(
            actor_id=self.fb_groups_scraper,
            input_data=input_data,
            wait_for_finish=True,
            timeout_secs=180
        )
        
        if not run_info:
            return None
        
        run_id = run_info.get("id")
        if not run_id:
            return None
        
        return await self.get_run_dataset(run_id)
    
    # ========== Utility Methods ==========
    
    async def wait_for_run(
        self,
        run_id: str,
        max_wait_seconds: int = 300,
        poll_interval: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        המתנה לסיום run
        """
        elapsed = 0
        
        while elapsed < max_wait_seconds:
            status = await self.get_run_status(run_id)
            
            if not status:
                return None
            
            run_status = status.get("status")
            
            if run_status == "SUCCEEDED":
                return status
            elif run_status in ["FAILED", "ABORTED", "TIMED-OUT"]:
                logger.error(f"🎭 ❌ Run {run_id} ended with status: {run_status}")
                return status
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.warning(f"🎭 ⚠️ Timeout waiting for run {run_id}")
        return None


# Singleton
_apify_service: Optional[ApifyService] = None


def get_apify_service() -> ApifyService:
    """קבלת instance של Apify Service"""
    global _apify_service
    if _apify_service is None:
        _apify_service = ApifyService()
    return _apify_service
