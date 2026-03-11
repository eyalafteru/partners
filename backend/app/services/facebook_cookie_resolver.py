"""
Facebook Cookie Resolver - החזרת Cookie לפרסום לפי פרופיל פעיל.

סדר עדיפות:
1. פרופיל פעיל מטבלת facebook_publishing_profiles
2. fallback: facebook_cookie_storage id=1
3. fallback: .env FACEBOOK_COOKIE
"""
from typing import Optional, Tuple
import json
import pymysql
from loguru import logger

from app.config import settings as cfg


def get_facebook_cookies_for_publishing() -> Tuple[Optional[str], Optional[str]]:
    """
    מחזיר (cookie_json_str, profile_name) לשימוש בפרסום.
    cookie_json_str: מחרוזת JSON של מערך cookies, או None אם אין.
    profile_name: שם הפרופיל שממנו נלקח (להלוג), או None.
    """
    # 1) פרופיל פעיל מ-facebook_publishing_profiles
    try:
        conn = pymysql.connect(
            host=cfg.db_host,
            port=cfg.db_port,
            user=cfg.db_user,
            password=cfg.db_password,
            database=cfg.db_name,
            autocommit=True,
        )
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cookie_json, name FROM facebook_publishing_profiles WHERE is_active = 1 LIMIT 1"
            )
            row = cursor.fetchone()
            cursor.close()
            if row and row[0]:
                logger.debug(f"🍪 Cookie for publishing from profile: {row[1]}")
                return (row[0], row[1])
            # אין פרופיל פעיל – ננסה פרופיל ראשון (לפי id)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT cookie_json, name FROM facebook_publishing_profiles WHERE cookie_json IS NOT NULL AND cookie_json != '' ORDER BY id LIMIT 1"
            )
            row = cursor.fetchone()
            cursor.close()
            if row and row[0]:
                logger.debug(f"🍪 Cookie for publishing from first profile: {row[1]}")
                return (row[0], row[1])
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"🍪 facebook_publishing_profiles not available: {e}")

    # 2) Legacy: facebook_cookie_storage id=1
    try:
        conn = pymysql.connect(
            host=cfg.db_host,
            port=cfg.db_port,
            user=cfg.db_user,
            password=cfg.db_password,
            database=cfg.db_name,
            autocommit=True,
        )
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT cookie_json FROM facebook_cookie_storage WHERE id = 1")
            row = cursor.fetchone()
            cursor.close()
            if row and row[0]:
                logger.debug("🍪 Cookie for publishing from facebook_cookie_storage (legacy)")
                return (row[0], None)
        finally:
            conn.close()
    except Exception as e:
        logger.debug(f"🍪 facebook_cookie_storage read failed: {e}")

    # 3) .env
    env_cookie = (getattr(cfg, "facebook_cookie", "") or "").strip()
    if env_cookie:
        logger.debug("🍪 Cookie for publishing from .env")
        return (env_cookie, None)

    return (None, None)
