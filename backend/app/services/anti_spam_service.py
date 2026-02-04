"""
Anti-Spam Service for Facebook Marketing
מנגנון הגנה מפני חסימות בפייסבוק
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple
import random
import asyncio

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.facebook_marketing import FacebookPost, FacebookGroup

logger = logging.getLogger(__name__)


class AntiSpamService:
    """מנגנון Anti-Spam לפייסבוק"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.settings = settings
    
    async def can_post_now(self) -> Tuple[bool, str]:
        """
        בדיקה האם מותר לפרסם עכשיו
        
        Returns:
            (מותר?, סיבה)
        """
        # 1. בדיקת שעות פרסום
        current_hour = datetime.now().hour
        if current_hour < self.settings.fb_posting_hours_start:
            return False, f"⏰ מוקדם מדי - פרסום מתחיל ב-{self.settings.fb_posting_hours_start}:00"
        
        if current_hour >= self.settings.fb_posting_hours_end:
            return False, f"⏰ מאוחר מדי - פרסום נעצר ב-{self.settings.fb_posting_hours_end}:00"
        
        # 2. בדיקת מגבלת פוסטים יומית
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        posts_today = await self.session.execute(
            select(func.count(FacebookPost.id)).where(
                FacebookPost.published_at >= today_start,
                FacebookPost.status == "published"
            )
        )
        count_today = posts_today.scalar() or 0
        
        if count_today >= self.settings.fb_max_posts_per_day:
            return False, f"🚫 הגעת למגבלה היומית ({self.settings.fb_max_posts_per_day} פוסטים)"
        
        # 3. בדיקת השהייה מהפוסט האחרון
        last_post = await self.session.execute(
            select(FacebookPost).where(
                FacebookPost.status == "published"
            ).order_by(FacebookPost.published_at.desc()).limit(1)
        )
        last_post = last_post.scalar_one_or_none()
        
        if last_post and last_post.published_at:
            seconds_since_last = (datetime.now() - last_post.published_at).total_seconds()
            if seconds_since_last < self.settings.fb_min_delay_between_posts:
                wait_time = int(self.settings.fb_min_delay_between_posts - seconds_since_last)
                return False, f"⏳ המתן עוד {wait_time} שניות לפני הפוסט הבא"
        
        return True, "✅ מותר לפרסם"
    
    async def can_post_to_group(self, group_id: int) -> Tuple[bool, str]:
        """
        בדיקה האם מותר לפרסם לקבוצה מסוימת
        
        Args:
            group_id: מזהה הקבוצה
            
        Returns:
            (מותר?, סיבה)
        """
        # בדיקה כללית
        can_post, reason = await self.can_post_now()
        if not can_post:
            return False, reason
        
        # בדיקת מגבלה שבועית לקבוצה
        week_ago = datetime.now() - timedelta(days=7)
        posts_to_group = await self.session.execute(
            select(func.count(FacebookPost.id)).where(
                FacebookPost.group_id == group_id,
                FacebookPost.published_at >= week_ago,
                FacebookPost.status == "published"
            )
        )
        count_to_group = posts_to_group.scalar() or 0
        
        if count_to_group >= self.settings.fb_max_posts_per_group_per_week:
            # מציאת התאריך הבא שמותר לפרסם
            oldest_post = await self.session.execute(
                select(FacebookPost).where(
                    FacebookPost.group_id == group_id,
                    FacebookPost.published_at >= week_ago,
                    FacebookPost.status == "published"
                ).order_by(FacebookPost.published_at.asc()).limit(1)
            )
            oldest = oldest_post.scalar_one_or_none()
            if oldest and oldest.published_at:
                next_allowed = oldest.published_at + timedelta(days=7)
                return False, f"🚫 כבר פרסמת לקבוצה זו השבוע. מותר שוב ב-{next_allowed.strftime('%d/%m/%Y')}"
            
            return False, "🚫 כבר פרסמת לקבוצה זו השבוע"
        
        return True, "✅ מותר לפרסם לקבוצה"
    
    async def get_random_delay(self) -> int:
        """
        קבלת השהייה אקראית בין פוסטים
        
        Returns:
            מספר שניות להמתנה
        """
        min_delay = self.settings.fb_min_delay_between_posts
        max_delay = self.settings.fb_max_delay_between_posts
        
        # השהייה אקראית + רכיב נוסף אקראי לטבעיות
        base_delay = random.randint(min_delay, max_delay)
        jitter = random.randint(-30, 60)  # +/- 30-60 שניות
        
        return max(min_delay, base_delay + jitter)
    
    async def wait_before_next_post(self) -> int:
        """
        המתנה לפני הפוסט הבא
        
        Returns:
            מספר השניות שהמתין
        """
        delay = await self.get_random_delay()
        logger.info(f"⏳ ממתין {delay} שניות לפני הפוסט הבא...")
        await asyncio.sleep(delay)
        return delay
    
    async def get_posting_stats(self) -> dict:
        """
        קבלת סטטיסטיקות פרסום
        
        Returns:
            מילון עם סטטיסטיקות
        """
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = datetime.now() - timedelta(days=7)
        
        # פוסטים היום
        posts_today_result = await self.session.execute(
            select(func.count(FacebookPost.id)).where(
                FacebookPost.published_at >= today_start,
                FacebookPost.status == "published"
            )
        )
        posts_today_count = posts_today_result.scalar() or 0
        
        # פוסטים השבוע
        posts_week_result = await self.session.execute(
            select(func.count(FacebookPost.id)).where(
                FacebookPost.published_at >= week_ago,
                FacebookPost.status == "published"
            )
        )
        posts_week_count = posts_week_result.scalar() or 0
        
        # קבוצות שפרסמנו אליהן השבוע
        groups_posted_result = await self.session.execute(
            select(func.count(func.distinct(FacebookPost.group_id))).where(
                FacebookPost.published_at >= week_ago,
                FacebookPost.status == "published"
            )
        )
        groups_posted_count = groups_posted_result.scalar() or 0
        
        return {
            "posts_today": posts_today_count,
            "max_posts_today": self.settings.fb_max_posts_per_day,
            "remaining_today": max(0, self.settings.fb_max_posts_per_day - posts_today_count),
            "posts_this_week": posts_week_count,
            "groups_posted_this_week": groups_posted_count,
            "posting_hours": f"{self.settings.fb_posting_hours_start}:00 - {self.settings.fb_posting_hours_end}:00",
            "min_delay_seconds": self.settings.fb_min_delay_between_posts,
            "max_delay_seconds": self.settings.fb_max_delay_between_posts,
            "current_hour": datetime.now().hour,
            "can_post_now": self.settings.fb_posting_hours_start <= datetime.now().hour < self.settings.fb_posting_hours_end
        }
    
    async def get_available_groups(self, campaign_group_ids: list) -> list:
        """
        קבלת קבוצות שמותר לפרסם אליהן
        
        Args:
            campaign_group_ids: רשימת קבוצות של הקמפיין
            
        Returns:
            רשימת קבוצות שמותר לפרסם אליהן
        """
        week_ago = datetime.now() - timedelta(days=7)
        
        # קבוצות שכבר פרסמנו אליהן השבוע
        posted_groups = await self.session.execute(
            select(FacebookPost.group_id).where(
                FacebookPost.group_id.in_(campaign_group_ids),
                FacebookPost.published_at >= week_ago,
                FacebookPost.status == "published"
            ).group_by(FacebookPost.group_id).having(
                func.count(FacebookPost.id) >= self.settings.fb_max_posts_per_group_per_week
            )
        )
        blocked_group_ids = {row[0] for row in posted_groups.fetchall()}
        
        # החזרת קבוצות שמותר לפרסם אליהן
        available = [gid for gid in campaign_group_ids if gid not in blocked_group_ids]
        
        logger.info(f"📊 קבוצות זמינות: {len(available)}/{len(campaign_group_ids)}")
        return available


def get_anti_spam_service(session: AsyncSession) -> AntiSpamService:
    """Factory function"""
    return AntiSpamService(session)
