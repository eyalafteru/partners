"""
Facebook Action Logger
לוג מרכזי של כל פעולה שנוגעת בפייסבוק -- לזיהוי חסימות ואכיפת מכסות.
"""
import time
from typing import Optional
from loguru import logger
from contextlib import asynccontextmanager

from app.database import get_async_session_context
from app.models.facebook_marketing import FacebookActionLog


ACTION_POST = "post"
ACTION_REPLY = "reply"
ACTION_SCRAPE_COMMENTS = "scrape_comments"
ACTION_SCRAPE_GROUPS = "scrape_groups"
ACTION_FIRST_COMMENT = "first_comment"

METHOD_APIFY_CUSTOM = "apify_custom_actor"
METHOD_APIFY_PUBLIC = "apify_public_scraper"
METHOD_APIFY_POSTER = "apify_poster"
METHOD_APIFY_LEGACY = "apify_legacy_poster"
METHOD_LOCAL_BROWSER = "local_browser"
METHOD_CHROME_EXT = "chrome_extension"
METHOD_FB_API = "facebook_api"


class _ActionTimer:
    """Context-object returned by fb_action_log(); call .finish() when done."""

    def __init__(
        self,
        action_type: str,
        method: str,
        profile_name: Optional[str] = None,
        profile_id: Optional[int] = None,
        target_url: Optional[str] = None,
        post_id: Optional[int] = None,
        reply_id: Optional[int] = None,
        group_name: Optional[str] = None,
    ):
        self.action_type = action_type
        self.method = method
        self.profile_name = profile_name
        self.profile_id = profile_id
        self.target_url = target_url
        self.post_id = post_id
        self.reply_id = reply_id
        self.group_name = group_name
        self._start = time.monotonic()

    async def finish(
        self,
        success: bool,
        apify_run_id: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        duration_ms = int((time.monotonic() - self._start) * 1000)

        try:
            async with get_async_session_context() as session:
                log_entry = FacebookActionLog(
                    action_type=self.action_type,
                    method=self.method,
                    profile_name=self.profile_name,
                    profile_id=self.profile_id,
                    target_url=self.target_url,
                    post_id=self.post_id,
                    reply_id=self.reply_id,
                    group_name=self.group_name,
                    apify_run_id=apify_run_id,
                    success=success,
                    error_message=error_message[:2000] if error_message else None,
                    duration_ms=duration_ms,
                )
                session.add(log_entry)

            status = "✅" if success else "❌"
            logger.info(
                f"📊 FB-LOG {status} {self.action_type}/{self.method} "
                f"profile={self.profile_name} duration={duration_ms}ms "
                f"url={self.target_url}"
            )
        except Exception as e:
            logger.error(f"📊 FB-LOG write failed (non-blocking): {e}")


def fb_action_log(
    action_type: str,
    method: str,
    profile_name: Optional[str] = None,
    profile_id: Optional[int] = None,
    target_url: Optional[str] = None,
    post_id: Optional[int] = None,
    reply_id: Optional[int] = None,
    group_name: Optional[str] = None,
) -> _ActionTimer:
    """
    Start tracking a Facebook action.

    Usage::

        tracker = fb_action_log(ACTION_POST, METHOD_APIFY_POSTER, target_url=group_url)
        # ... do the work ...
        await tracker.finish(success=True, apify_run_id=run_id)
    """
    return _ActionTimer(
        action_type=action_type,
        method=method,
        profile_name=profile_name,
        profile_id=profile_id,
        target_url=target_url,
        post_id=post_id,
        reply_id=reply_id,
        group_name=group_name,
    )
