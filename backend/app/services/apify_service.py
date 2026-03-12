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
from app.services.facebook_cookie_resolver import get_facebook_cookies_for_publishing
from app.services.facebook_action_logger import (
    fb_action_log,
    ACTION_POST, ACTION_REPLY, ACTION_SCRAPE_COMMENTS, ACTION_FIRST_COMMENT,
    METHOD_APIFY_CUSTOM, METHOD_APIFY_PUBLIC, METHOD_APIFY_POSTER, METHOD_APIFY_LEGACY,
)


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
        
        # Facebook cookies - try DB first, fallback to .env
        self.facebook_cookie = settings.facebook_cookie
        self._active_profile_name: Optional[str] = None
        self._load_cookies_from_db()
    
    def _load_cookies_from_db(self):
        """טעינת cookies לפרסום: פרופיל פעיל, אחרת legacy storage / .env"""
        cookie_str, profile_name = get_facebook_cookies_for_publishing()
        if cookie_str:
            self.facebook_cookie = cookie_str
            self._active_profile_name = profile_name
            src = f"profile '{profile_name}'" if profile_name else "DB/env"
            logger.info(f"🍪 Cookies loaded from {src}")
            return True
        return False

    def reload_cookies(self):
        """טעינה מחדש של cookies (פרופיל פעיל) והגדרות Actor"""
        if self._load_cookies_from_db():
            new_settings = reload_settings()
            self.fb_poster_custom_actor = new_settings.apify_fb_poster_custom_actor
            return
        new_settings = reload_settings()
        self.facebook_cookie = new_settings.facebook_cookie
        self.fb_poster_custom_actor = new_settings.apify_fb_poster_custom_actor
        logger.info("🍪 Cookies reloaded from .env settings")
    
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
    
    def get_own_fb_user_id(self) -> Optional[str]:
        """זיהוי ה-Facebook user ID שלנו מתוך ה-cookies (c_user)"""
        try:
            cookies = self._parse_cookie()
            for c in cookies:
                if c.get("name") == "c_user":
                    return c.get("value")
        except:
            pass
        return None
    
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
            method = METHOD_APIFY_POSTER
            tracker = fb_action_log(
                ACTION_POST, method,
                profile_name=self._active_profile_name,
                target_url=group_urls[0] if group_urls else None,
            )
            input_data = {
                "facebookCookies": cookie_array,
                "groupUrls": group_urls,
                "messages": messages,
                "delayMinSeconds": max(delay_seconds, 300),
                "delayMaxSeconds": max(delay_seconds * 3, 900),
                "maxPostsPerRun": len(group_urls),
            }
            
            result = await self.run_actor(
                actor_id=self.fb_poster_custom_actor,
                input_data=input_data,
                wait_for_finish=False
            )
            await tracker.finish(
                success=result is not None,
                apify_run_id=result.get("id") if result else None,
                error_message=None if result else "run_actor returned None",
            )
            return result
        
        # ==== Legacy Actor (bhansalisoft) ====
        logger.info(f"🎭 Using LEGACY actor: {self.fb_poster_actor}")
        method = METHOD_APIFY_LEGACY
        tracker = fb_action_log(
            ACTION_POST, method,
            profile_name=self._active_profile_name,
            target_url=group_urls[0] if group_urls else None,
        )
        input_data = {
            "Facebook_Profile_URL": group_urls,
            "Message": messages,
            "Delay": str(delay_seconds),
            "Cookies": cookie_array
        }
        
        if use_proxy:
            input_data["proxyConfiguration"] = {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "IL"
            }
            logger.info("🎭 🇮🇱 Using Israeli Residential Proxy")
        
        logger.info(f"🎭 Actor input: {len(group_urls)} groups, {len(messages)} messages, delay={delay_seconds}s")
        
        result = await self.run_actor(
            actor_id=self.fb_poster_actor,
            input_data=input_data,
            wait_for_finish=False
        )
        await tracker.finish(
            success=result is not None,
            apify_run_id=result.get("id") if result else None,
            error_message=None if result else "run_actor returned None",
        )
        return result
    
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
        sort_by: str = "RANKED_UNFILTERED"
    ) -> Optional[Dict[str, Any]]:
        """
        סריקת תגובות מפוסטים
        
        Args:
            post_urls: רשימת URLs של פוסטים
            max_comments: מקסימום תגובות לסרוק
            sort_by: מיון (RANKED_UNFILTERED = non-filtered, newest, most_relevant)
            
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
        קבלת תגובות מפוסט ספציפי.
        מנסה קודם סורק ציבורי (ללא cookies, ללא סיכון לחשבון),
        ורק אם נכשל (למשל קבוצה סגורה) -- נופל ל-custom actor עם cookies.
        
        Returns:
            רשימת תגובות
        """
        # ===== ניסיון 1: סורק ציבורי (בלי cookies, בלי סיכון) =====
        logger.info(f"🎭 get_post_comments: trying public scraper first (no cookies)")
        tracker = fb_action_log(
            ACTION_SCRAPE_COMMENTS, METHOD_APIFY_PUBLIC,
            target_url=post_url,
        )
        try:
            comments = await self._scrape_with_public_actor(post_url, max_comments)
            if comments and len(comments) > 0:
                logger.info(f"🎭 ✅ Public scraper found {len(comments)} comments")
                await tracker.finish(success=True)
                return comments
            else:
                logger.warning("🎭 ⚠️ Public scraper returned no comments")
                await tracker.finish(success=False, error_message="No comments returned")
        except Exception as e:
            logger.warning(f"🎭 ⚠️ Public scraper failed: {e}")
            await tracker.finish(success=False, error_message=str(e))
        
        # ===== ניסיון 2: Custom actor עם cookies (רק כ-fallback לקבוצות סגורות) =====
        self._load_cookies_from_db()
        current_settings = reload_settings()
        custom_actor = current_settings.apify_fb_comment_reply_actor
        
        if custom_actor and self.has_facebook_cookie:
            logger.info(f"🎭 Public scraper failed, falling back to custom actor with cookies: {custom_actor}")
            tracker2 = fb_action_log(
                ACTION_SCRAPE_COMMENTS, METHOD_APIFY_CUSTOM,
                profile_name=self._active_profile_name,
                target_url=post_url,
            )
            try:
                comments = await self._scrape_with_custom_actor(custom_actor, post_url)
                if comments and len(comments) > 0:
                    logger.info(f"🎭 ✅ Custom scraper found {len(comments)} comments")
                    await tracker2.finish(success=True)
                    return comments
                else:
                    await tracker2.finish(success=False, error_message="No comments returned")
            except Exception as e:
                logger.warning(f"🎭 ⚠️ Custom scraper also failed: {e}")
                await tracker2.finish(success=False, error_message=str(e))
        
        logger.warning(f"🎭 ❌ No comments found for {post_url}")
        return None
    
    async def _scrape_with_custom_actor(
        self,
        actor_id: str,
        post_url: str
    ) -> Optional[List[Dict[str, Any]]]:
        """סריקת תגובות באמצעות ה-Actor המותאם שלנו (Playwright + cookies)"""
        input_data = {
            "postUrl": post_url,
            "mode": "scrape",
            "cookies": self._parse_cookie(),
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "IL"
            }
        }
        
        run_info = await self.run_actor(
            actor_id=actor_id,
            input_data=input_data,
            wait_for_finish=True,
            timeout_secs=120
        )
        
        if not run_info:
            return None
        
        run_id = run_info.get("id")
        if not run_id:
            return None
        
        # אם עדיין רץ, ממתינים
        run_status = run_info.get("status", "")
        if run_status not in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            logger.info(f"🎭 Custom scraper still running, polling...")
            final_status = await self.wait_for_run(run_id, max_wait_seconds=120, poll_interval=5.0)
            if not final_status or final_status.get("status") != "SUCCEEDED":
                logger.warning(f"🎭 ⚠️ Custom scraper did not succeed")
                return None
        
        results = await self.get_run_dataset(run_id)
        
        if not results:
            return None
        
        # סינון תוצאות שגיאה (שורות עם success: false)
        comments = [r for r in results if not r.get("error") and r.get("profileName")]
        return comments if comments else None
    
    async def _scrape_with_public_actor(
        self,
        post_url: str,
        max_comments: int = 50
    ) -> Optional[List[Dict[str, Any]]]:
        """סריקת תגובות באמצעות ה-Apify public scraper (fallback)"""
        run_info = await self.scrape_post_comments(
            post_urls=[post_url],
            max_comments=max_comments
        )
        
        if not run_info:
            return None
        
        run_id = run_info.get("id")
        if not run_id:
            return None
        
        # אם ה-run עדיין רץ, ממתינים
        run_status = run_info.get("status", "")
        if run_status not in ["SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"]:
            logger.info(f"🎭 Public scraper still running ({run_status}), polling...")
            final_status = await self.wait_for_run(run_id, max_wait_seconds=180, poll_interval=5.0)
            if not final_status or final_status.get("status") != "SUCCEEDED":
                logger.warning(f"🎭 ⚠️ Public scraper did not succeed")
        
        raw_comments = await self.get_run_dataset(run_id)
        
        if not raw_comments:
            return None
        
        # Flatten: חילוץ תת-תגובות
        all_comments = []
        for comment in raw_comments:
            all_comments.append(comment)
            sub_comments = comment.get("comments", [])
            if sub_comments:
                for sub in sub_comments:
                    if "inputUrl" not in sub:
                        sub["inputUrl"] = comment.get("inputUrl")
                    all_comments.append(sub)
        
        logger.info(f"🎭 Public scraper: {len(raw_comments)} top-level + {len(all_comments) - len(raw_comments)} sub = {len(all_comments)} total")
        return all_comments
    
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
        שליחת תגובה לתגובה בפוסט פייסבוק באמצעות Apify actor עם Playwright.
        """
        self._load_cookies_from_db()
        
        tracker = fb_action_log(
            ACTION_REPLY, METHOD_APIFY_CUSTOM,
            profile_name=self._active_profile_name,
            target_url=post_url,
        )
        
        if not self.has_facebook_cookie:
            logger.error("🎭 ❌ Facebook cookie not configured for comment reply")
            await tracker.finish(success=False, error_message="Cookie not configured")
            return {"success": False, "error": "Facebook cookie לא מוגדר"}
        
        current_settings = reload_settings()
        comment_reply_actor = current_settings.apify_fb_comment_reply_actor
        
        if not comment_reply_actor:
            logger.warning("🎭 ⚠️ APIFY_FB_COMMENT_REPLY_ACTOR not configured")
            await tracker.finish(success=False, error_message="Actor not configured")
            return {
                "success": False,
                "error": "Actor לתגובות לא מוגדר. יש להגדיר APIFY_FB_COMMENT_REPLY_ACTOR.",
                "manual_required": True
            }
        
        logger.info(f"🎭 Using comment reply actor: {comment_reply_actor}")
        
        input_data = {
            "postUrl": post_url,
            "replyMessage": reply_message,
            "cookies": self._parse_cookie(),
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
                "apifyProxyCountry": "IL"
            }
        }
        if comment_id:
            input_data["commentId"] = comment_id
        
        run_info = await self.run_actor(
            actor_id=comment_reply_actor,
            input_data=input_data,
            wait_for_finish=True,
            timeout_secs=120
        )
        
        if not run_info:
            logger.error("🎭 ❌ Failed to start comment reply actor")
            await tracker.finish(success=False, error_message="Failed to start Apify actor run")
            return {"success": False, "error": "Failed to start Apify actor run"}
        
        run_id = run_info.get("id")
        run_status = run_info.get("status", "UNKNOWN")
        
        if run_status in ["FAILED", "ABORTED", "TIMED-OUT"]:
            logger.error(f"🎭 ❌ Comment reply actor run {run_status}: {run_id}")
            await tracker.finish(success=False, apify_run_id=run_id, error_message=f"Actor run {run_status}")
            return {"success": False, "error": f"Actor run {run_status}"}
        
        if run_id:
            results = await self.get_run_dataset(run_id)
            if results and len(results) > 0:
                result = results[0]
                if result.get("success"):
                    logger.info(f"🎭 ✅ Comment reply sent via Apify actor (run: {run_id})")
                    await tracker.finish(success=True, apify_run_id=run_id)
                    return result
                else:
                    error_msg = result.get("error", "Unknown error from actor")
                    logger.error(f"🎭 ❌ Apify actor failed: {error_msg}")
                    await tracker.finish(success=False, apify_run_id=run_id, error_message=error_msg)
                    return result
            else:
                logger.warning(f"🎭 ⚠️ No dataset results from run {run_id} - actor may have crashed")
                await tracker.finish(success=False, apify_run_id=run_id, error_message="No dataset results - actor may have crashed")
                return {"success": False, "error": "Actor did not return results - check Apify console"}
        
        await tracker.finish(success=False, error_message="No run ID returned")
        return {"success": False, "error": "No run ID returned"}
    
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


