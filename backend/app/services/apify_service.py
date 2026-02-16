"""
PartnerCalc OS - Apify Integration Service
שירות לאינטגרציה עם Apify לפייסבוק
"""
import httpx
import asyncio
import json
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings, reload_settings


class ApifyService:
    """שירות אינטגרציה עם Apify"""
    
    def __init__(self):
        self.api_token = settings.apify_token
        self.base_url = "https://api.apify.com/v2"
        
        # Actor IDs
        self.fb_poster_actor = settings.apify_fb_poster_actor
        self.fb_poster_custom_actor = settings.apify_fb_poster_custom_actor
        self.fb_comments_actor = settings.apify_fb_comments_actor
        self.fb_messenger_actor = settings.apify_fb_messenger_actor
        self.fb_groups_scraper = settings.apify_fb_groups_scraper
        
        # Facebook cookies - JSON array format only
        self.facebook_cookie = settings.facebook_cookie
    
    def reload_cookies(self):
        """טעינה מחדש של cookies מהגדרות (אחרי עדכון .env)"""
        new_settings = reload_settings()
        self.facebook_cookie = new_settings.facebook_cookie
        self.fb_poster_custom_actor = new_settings.apify_fb_poster_custom_actor
        logger.info("🍪 Cookies reloaded from settings")
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.api_token)
    
    @property
    def has_facebook_cookie(self) -> bool:
        """בדיקה אם יש Facebook cookie"""
        return bool(self.facebook_cookie)
    
    @property
    def use_custom_actor(self) -> bool:
        """בדיקה אם משתמשים באקטור מותאם אישית"""
        return bool(self.fb_poster_custom_actor)
    
    def _get_headers(self) -> Dict[str, str]:
        """הכנת headers לקריאות API"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def _normalize_same_site(value: str) -> str:
        """
        נרמול ערך sameSite לפורמט שתואם ל-Playwright/Apify
        Chrome מחזיר ערכים כמו 'no_restriction', 'unspecified' וכו'
        Playwright מצפה ל: 'Strict', 'Lax', או 'None'
        """
        mapping = {
            "strict": "Strict",
            "lax": "Lax",
            "none": "None",
            "no_restriction": "None",
            "no restriction": "None",
            "unspecified": "Lax",
        }
        return mapping.get(str(value).lower(), "Lax")

    def _parse_cookie(self) -> List[Dict[str, Any]]:
        """המרת cookie מ-string ל-list, עם נרמול sameSite"""
        if not self.facebook_cookie:
            return []
        
        try:
            if isinstance(self.facebook_cookie, str):
                cookies = json.loads(self.facebook_cookie)
            else:
                cookies = self.facebook_cookie
            
            # נרמול sameSite לכל cookie
            for cookie in cookies:
                if "sameSite" in cookie:
                    cookie["sameSite"] = self._normalize_same_site(cookie["sameSite"])
            
            return cookies
        except:
            logger.error("Failed to parse Facebook cookie")
            return []
    
    def _get_cookie_string(self) -> str:
        """קבלת cookie בפורמט string"""
        try:
            cookies = self._parse_cookie()
            if cookies:
                return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        except:
            logger.error("Failed to convert cookie to string")
        
        return ""
    
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
        delay_seconds: int = 60,
        use_proxy: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        פרסום לקבוצות פייסבוק
        משתמש באקטור מותאם אישית אם מוגדר, אחרת בישן
        
        Args:
            group_urls: רשימת URLs של קבוצות
            messages: רשימת הודעות
            delay_seconds: השהייה בין פוסטים
            use_proxy: האם להשתמש בפרוקסי ישראלי (ברירת מחדל: כן)
            
        Returns:
            run info
        """
        if not self.has_facebook_cookie:
            logger.error("🎭 ❌ Facebook cookie not configured")
            return None
        
        cookie_array = self._parse_cookie()
        
        if not cookie_array:
            logger.error("🎭 ❌ Failed to parse Facebook cookie as array")
            return None
        
        logger.info(f"🎭 Posting to {len(group_urls)} groups with {len(cookie_array)} cookies (proxy: {use_proxy})")
        logger.debug(f"🎭 Cookie names: {[c.get('name') for c in cookie_array]}")
        
        # ==== Custom Actor (preferred) ====
        if self.use_custom_actor:
            logger.info(f"🎭 Using CUSTOM actor: {self.fb_poster_custom_actor}")
            input_data = {
                "facebookCookies": cookie_array,
                "groupUrls": group_urls,
                "messages": messages,
                "delayMinSeconds": max(delay_seconds, 300),
                "delayMaxSeconds": max(delay_seconds * 3, 900),
                "maxPostsPerRun": len(group_urls),
            }
            
            return await self.run_actor(
                actor_id=self.fb_poster_custom_actor,
                input_data=input_data,
                wait_for_finish=False
            )
        
        # ==== Legacy Actor (bhansalisoft) ====
        logger.info(f"🎭 Using LEGACY actor: {self.fb_poster_actor}")
        input_data = {
            "Facebook_Profile_URL": group_urls,
            "Message": messages,
            "Delay": str(delay_seconds),
            "Cookies": cookie_array
        }
        
        # הוספת פרוקסי ישראלי Residential למניעת חסימות
        if use_proxy:
            input_data["proxyConfiguration"] = {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "IL"
            }
            logger.info("🎭 🇮🇱 Using Israeli Residential Proxy")
        
        logger.info(f"🎭 Actor input: {len(group_urls)} groups, {len(messages)} messages, delay={delay_seconds}s")
        
        return await self.run_actor(
            actor_id=self.fb_poster_actor,
            input_data=input_data,
            wait_for_finish=False
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
    
    # ========== Facebook Comment Reply ==========
    
    async def reply_to_comment(
        self,
        post_url: str,
        reply_message: str,
        comment_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        שליחת תגובה לתגובה בפוסט פייסבוק
        
        Args:
            post_url: URL הפוסט
            reply_message: תוכן התגובה
            comment_id: מזהה התגובה להגיב עליה (אופציונלי)
            
        Returns:
            dict עם תוצאת הפעולה או None בשגיאה
        """
        if not self.has_facebook_cookie:
            logger.error("🎭 ❌ Facebook cookie not configured for comment reply")
            return None
        
        # בדיקה שה-Actor מוגדר
        comment_reply_actor = settings.apify_fb_comment_reply_actor
        if not comment_reply_actor:
            logger.warning("🎭 ⚠️ Comment reply actor not configured - skipping")
            return None
        
        input_data = {
            "postUrl": post_url,
            "replyMessage": reply_message,
            "cookies": self._parse_cookie()
        }
        
        if comment_id:
            input_data["commentId"] = comment_id
        
        # הרצת ה-Actor והמתנה לסיום
        run_info = await self.run_actor(
            actor_id=comment_reply_actor,
            input_data=input_data,
            wait_for_finish=True,
            timeout_secs=120
        )
        
        if not run_info:
            return None
        
        run_id = run_info.get("id")
        if not run_id:
            return None
        
        # קבלת התוצאות
        results = await self.get_run_dataset(run_id)
        
        if results and len(results) > 0:
            result = results[0]
            if result.get("success"):
                logger.info(f"🎭 ✅ Comment reply sent successfully")
                return result
            else:
                logger.error(f"🎭 ❌ Comment reply failed: {result.get('error')}")
                return result
        
        return None
    
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
