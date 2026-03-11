"""
Local Browser Service - Playwright-based Facebook automation
Runs locally (same machine/IP as the cookies) for reliable authentication.
"""
import json
import asyncio
import random
import re
from typing import Optional, Dict, Any, List
from loguru import logger
import pymysql

from app.config import settings as cfg
from app.services.facebook_cookie_resolver import get_facebook_cookies_for_publishing


class LocalBrowserService:
    """
    שירות אוטומציית דפדפן מקומי עם Playwright.
    רץ על אותו מחשב שבו נוצרו הקוקיז - מבטיח אימות אמין מול פייסבוק.
    """

    def __init__(self):
        self._cookies_raw: Optional[str] = None

    def _load_cookies_from_db(self) -> List[Dict[str, Any]]:
        """טעינת קוקיז לפרסום: פרופיל פעיל, אחרת legacy storage / .env"""
        cookie_str, profile_name = get_facebook_cookies_for_publishing()
        if not cookie_str:
            return []
        try:
            cookies = json.loads(cookie_str) if isinstance(cookie_str, str) else cookie_str
            if isinstance(cookies, list) and len(cookies) > 0:
                src = f"profile '{profile_name}'" if profile_name else "DB/env"
                logger.info(f"🍪 Local browser: loaded {len(cookies)} cookies from {src}")
                return cookies
        except Exception as e:
            logger.warning(f"🍪 Local browser: failed to parse cookie JSON: {e}")
        return []

    @staticmethod
    def _normalize_same_site(value: str) -> str:
        mapping = {
            "strict": "Strict",
            "lax": "Lax",
            "none": "None",
            "no_restriction": "None",
            "no restriction": "None",
            "unspecified": "Lax",
        }
        return mapping.get(str(value).lower(), "Lax")

    def _prepare_cookies_for_playwright(self, cookies: List[Dict]) -> List[Dict]:
        """המרת קוקיז לפורמט של Playwright"""
        result = []
        for c in cookies:
            cookie = {
                "name": c.get("name", ""),
                "value": c.get("value", ""),
                "domain": c.get("domain", ".facebook.com"),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", True),
            }
            if c.get("sameSite"):
                cookie["sameSite"] = self._normalize_same_site(c["sameSite"])
            if c.get("expires") and c["expires"] > 0:
                cookie["expires"] = int(c["expires"])
            result.append(cookie)
        return result

    @staticmethod
    def _random_delay(min_ms: int, max_ms: int) -> float:
        return random.randint(min_ms, max_ms) / 1000.0

    @staticmethod
    def _extract_post_id_from_url(post_url: str) -> Optional[str]:
        """Extract post ID from Facebook URL (e.g. .../posts/1484559149735885 -> 1484559149735885)."""
        if not post_url:
            return None
        m = re.search(r"/posts/(\d+)", post_url)
        if m:
            return m.group(1)
        m = re.search(r"[\?&]id=(\d+)", post_url)
        if m:
            return m.group(1)
        return None

    async def reply_to_comment(
        self,
        post_url: str,
        reply_message: str,
        comment_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        פרסום תגובה בפייסבוק באמצעות Playwright מקומי.
        Returns: {"success": True/False, "error": "..."}
        """
        from playwright.async_api import async_playwright

        cookies = self._load_cookies_from_db()
        if not cookies:
            return {"success": False, "error": "No cookies found in DB"}

        pw_cookies = self._prepare_cookies_for_playwright(cookies)
        browser = None

        try:
            logger.info("🖥️ Opening local browser window (Chrome) - check this machine for the window!")
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(
                headless=False,  # must be False so user sees the window
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--window-size=1920,1080",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="he-IL",
                timezone_id="Asia/Jerusalem",
                extra_http_headers={
                    "Accept-Language": "he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7"
                },
            )

            # Stealth
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' },
                    ],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['he-IL', 'he', 'en-US', 'en'],
                });
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)

            # Set cookies
            await context.add_cookies(pw_cookies)
            logger.info(f"🍪 Set {len(pw_cookies)} cookies in local browser")

            page = await context.new_page()

            # Extract post ID so we only interact with THIS post (not ads/other posts)
            post_id_in_url = self._extract_post_id_from_url(post_url)
            if not post_id_in_url:
                return {"success": False, "error": f"Could not extract post ID from URL: {post_url}"}
            logger.info(f"🎯 Target post ID: {post_id_in_url} (will reply only on this post)")

            # Navigate to post
            logger.info(f"🌐 Navigating to: {post_url}")
            await page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(self._random_delay(5000, 8000))

            # Verify we're still on the correct post URL (Facebook sometimes redirects)
            current_url = page.url
            if post_id_in_url not in current_url:
                logger.error(f"❌ Wrong page: expected URL containing {post_id_in_url}, got {current_url}")
                try:
                    await page.screenshot(path="c:/Users/eyal/collab-system/debug-local-wrong-page.png")
                except Exception:
                    pass
                await asyncio.sleep(5)
                return {"success": False, "error": f"Landed on wrong page (URL does not contain post {post_id_in_url})"}

            # Save debug screenshot
            try:
                debug_path = "c:/Users/eyal/collab-system/debug-local-initial.png"
                await page.screenshot(path=debug_path)
                logger.info(f"📸 Debug screenshot saved: {debug_path}")
            except Exception:
                pass

            # Close any popups/dialogs (login popup, cookie consent, etc)
            logger.info("🔍 Checking for popups to close...")
            for attempt in range(5):
                closed_something = False
                # Try closing via aria-label
                for label in ["Close", "סגירה", "close", "Not Now", "לא עכשיו"]:
                    try:
                        close_btn = await page.query_selector(f'[aria-label="{label}"]')
                        if close_btn:
                            is_visible = await close_btn.is_visible()
                            if is_visible:
                                await close_btn.click(force=True, timeout=3000)
                                logger.info(f"🔒 Closed popup via aria-label='{label}'")
                                closed_something = True
                                await asyncio.sleep(1)
                                break
                    except Exception as e:
                        logger.debug(f"Could not click '{label}': {e}")
                
                # Try closing dialog via Escape key
                if not closed_something:
                    try:
                        dialog = await page.query_selector('div[role="dialog"]')
                        if dialog and await dialog.is_visible():
                            await page.keyboard.press("Escape")
                            logger.info("🔒 Closed dialog via Escape key")
                            closed_something = True
                            await asyncio.sleep(1)
                    except Exception:
                        pass

                if not closed_something:
                    break

            # Check login status
            logger.info(f"📍 Current URL: {page.url}")
            
            # Check for login indicators
            login_banner = await page.query_selector('text="Log in or sign up"')
            login_bar = await page.evaluate("""() => {
                const html = document.body.innerHTML;
                return html.includes('Log In') && html.includes('Create new account');
            }""")
            
            has_comment_form = await page.query_selector('[aria-label*="Write a comment"], [aria-label*="כתיבת תגובה"], div[contenteditable="true"]')
            
            if has_comment_form:
                logger.info("✅ Logged in to Facebook (comment editor detected)")
            elif login_banner or login_bar:
                logger.warning("⚠️ Not fully logged in - login banner detected")
                # Save screenshot for debugging
                try:
                    await page.screenshot(path="c:/Users/eyal/collab-system/debug-local-not-logged-in.png")
                except Exception:
                    pass
                # Don't return yet - try anyway since cookies might be partially working
            else:
                logger.info("✅ Logged in to Facebook (no login banner detected)")

            # Scroll down to load comments
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 400)")
                await asyncio.sleep(self._random_delay(600, 1000))

            # If comment_id provided, try clicking "Reply" on that comment
            if comment_id:
                logger.info(f"🎯 Looking for reply button for comment: {comment_id}")
                clicked_reply = await self._click_reply_button(page)
                if clicked_reply:
                    logger.info("✅ Clicked reply button for specific comment")
                else:
                    logger.info("ℹ️ No specific reply button found, posting as top-level comment")

            # Find comment editor ONLY within the target post (not under ads/other posts)
            editor = await self._find_comment_editor(page, post_id_in_url)
            if not editor:
                try:
                    await page.screenshot(path="c:/Users/eyal/collab-system/debug-local-no-editor.png", full_page=True)
                    logger.info("📸 Saved debug screenshot: debug-local-no-editor.png")
                except Exception:
                    pass
                logger.info("⏳ Leaving browser open 8 seconds so you can see the page...")
                await asyncio.sleep(8)
                return {
                    "success": False,
                    "error": "Could not find comment editor on page",
                }

            logger.info(f"📝 Found comment editor, typing reply ({len(reply_message)} chars)...")

            # Type reply with human-like timing
            await editor.click()
            await asyncio.sleep(self._random_delay(300, 800))
            for char in reply_message:
                await page.keyboard.type(char, delay=random.randint(30, 80))
                if random.random() < 0.05:
                    await asyncio.sleep(self._random_delay(200, 600))
            await asyncio.sleep(self._random_delay(500, 1500))

            logger.info("📤 Submitting reply (Enter)...")
            await page.keyboard.press("Enter")
            await asyncio.sleep(self._random_delay(4000, 6000))

            # Verify
            content = await page.content()
            short = reply_message[:30]
            if short in content:
                logger.info("✅ Reply confirmed on page!")
            else:
                logger.warning("⚠️ Reply text not confirmed on page after submit")

            return {"success": True}

        except Exception as e:
            logger.error(f"❌ Local browser error: {e}")
            # Leave browser open a few seconds so user can see what happened
            if browser:
                try:
                    await asyncio.sleep(8)
                except Exception:
                    pass
            return {"success": False, "error": str(e)}

        finally:
            if browser:
                await browser.close()

    async def _click_reply_button(self, page) -> bool:
        """חיפוש ולחיצה על כפתור 'הגב' לתגובה ספציפית"""
        try:
            reply_labels = ["הגב", "הגבה", "Reply"]
            # Try role=button with text
            buttons = await page.query_selector_all('div[role="button"]')
            for btn in buttons:
                text = await btn.text_content()
                if text and text.strip() in reply_labels:
                    if await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(self._random_delay(1000, 2000))
                        return True
            # Try aria-label
            for label in reply_labels:
                btn = await page.query_selector(f'[aria-label="{label}"]')
                if btn and await btn.is_visible():
                    await btn.click()
                    await asyncio.sleep(self._random_delay(1000, 2000))
                    return True
        except Exception as e:
            logger.warning(f"⚠️ Error finding reply button: {e}")
        return False

    async def _find_main_post_container(self, page, post_id: str) -> Optional[Any]:
        """Find the DOM container (article) that belongs to our post ID - so we only reply there."""
        try:
            articles = await page.query_selector_all('div[role="article"]')
            for art in articles:
                link = await art.query_selector(f'a[href*="{post_id}"]')
                if link:
                    logger.info(f"🎯 Found main post container for post ID {post_id}")
                    return art
            logger.warning(f"⚠️ No article with link to post {post_id} found, will search full page")
        except Exception as e:
            logger.warning(f"⚠️ Error finding main post container: {e}")
        return None

    async def _find_comment_editor(self, page, post_id: Optional[str] = None) -> Optional[Any]:
        """
        חיפוש שדה תגובה - רק בתוך הפוסט עם ה-ID הנכון (לא בפרסומות/פוסטים אחרים).
        """
        scope = None
        if post_id:
            scope = await self._find_main_post_container(page, post_id)

        # Strategy 1: Editor only inside our post
        logger.info("🔍 Strategy 1: Looking for comment editor in target post...")
        editor = await self._find_visible_editor(page, scope)
        if editor:
            return editor

        # Strategy 2: Click placeholders inside our post
        if scope:
            logger.info("🔍 Strategy 2: Clicking placeholders in target post...")
            editor = await self._activate_comment_input(page, scope)
            if editor:
                return editor

        # Strategy 3: Fallback - scroll to top and try again (our post is usually first)
        logger.info("🔍 Strategy 3: Scrolling to top and retrying in target post...")
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1.5)
        scope = await self._find_main_post_container(page, post_id) if post_id else None
        editor = await self._find_visible_editor(page, scope)
        if editor:
            return editor

        # Strategy 4: Last resort - search full page (but log warning)
        if post_id:
            logger.warning("⚠️ Could not scope to target post, searching full page (risk of wrong post!)")
        editor = await self._find_visible_editor(page, None)
        if editor:
            return editor

        # Log debug info
        editable_info = await page.evaluate("""() => {
            const els = document.querySelectorAll('[contenteditable="true"]');
            return Array.from(els).map(el => ({
                visible: el.offsetParent !== null,
                width: el.offsetWidth,
                height: el.offsetHeight,
                label: el.getAttribute('aria-label') || '',
            }));
        }""")
        logger.error(f"❌ No editor found. Contenteditable elements: {json.dumps(editable_info)}")
        return None

    async def _find_visible_editor(self, page, scope: Optional[Any] = None) -> Optional[Any]:
        """חיפוש editor גלוי - אם scope ניתן, רק בתוך האלמנט הזה (הפוסט שלנו)."""
        root = scope if scope else page
        selectors = [
            'div[contenteditable="true"][aria-label*="תגובה"]',
            'div[contenteditable="true"][aria-label*="comment"]',
            'div[contenteditable="true"][aria-label*="Comment"]',
            'div[contenteditable="true"][aria-label*="Write"]',
            'div[contenteditable="true"][aria-label*="Reply"]',
            'div[contenteditable="true"][aria-label*="הגב"]',
            'div[contenteditable="true"][aria-label*="כתיבת"]',
            'div[contenteditable="true"][role="textbox"]',
            'p[contenteditable="true"]',
            'div[contenteditable="true"][data-lexical-editor="true"]',
            'div[contenteditable="true"]',
        ]
        for selector in selectors:
            try:
                elements = await root.query_selector_all(selector)
                for el in elements:
                    if not await el.is_visible():
                        continue
                    box = await el.bounding_box()
                    if box and box["width"] > 40 and box["height"] > 8:
                        label = await el.get_attribute("aria-label") or ""
                        logger.info(
                            f"📝 Found editor: selector='{selector}', "
                            f"label='{label}', "
                            f"size={int(box['width'])}x{int(box['height'])}"
                        )
                        return el
            except Exception:
                continue
        return None

    async def _activate_comment_input(self, page, scope: Optional[Any] = None) -> Optional[Any]:
        """ניסיון להפעיל שדה תגובה ע\"י לחיצה על placeholder - רק בתוך scope אם ניתן."""
        root = scope if scope else page
        selectors = [
            '[aria-label*="Write a comment"]',
            '[aria-label*="כתיבת תגובה"]',
            '[aria-label*="Write a reply"]',
            '[aria-label*="כתיבת תשובה"]',
            '[aria-label*="תגובה"]',
            '[placeholder*="comment"]',
            '[placeholder*="תגובה"]',
            'div[role="textbox"]',
        ]
        for selector in selectors:
            try:
                elements = await root.query_selector_all(selector)
                for el in elements:
                    if not await el.is_visible():
                        continue
                    logger.info(f"🖱️ Clicking placeholder: {selector}")
                    await el.click()
                    await asyncio.sleep(self._random_delay(1500, 2500))
                    editor = await self._find_visible_editor(page, scope)
                    if editor:
                        logger.info("📝 Editor activated after clicking placeholder")
                        return editor
            except Exception:
                continue
        return None


# Singleton
_local_browser_service: Optional[LocalBrowserService] = None


def get_local_browser_service() -> LocalBrowserService:
    global _local_browser_service
    if _local_browser_service is None:
        _local_browser_service = LocalBrowserService()
    return _local_browser_service
