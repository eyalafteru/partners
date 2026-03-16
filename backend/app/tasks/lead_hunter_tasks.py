"""
PartnerCalc OS - Lead Hunter Auto-Reply Tasks
משימות רקע לתגובה אוטומטית על פוסטים שנקלטו מפושר

הגנות בטיחות מפני חסימות פייסבוק:
- חלון שעות פעילות (07:00-22:00 שעון ישראל)
- מרווח מינימלי בין תגובות (8-15 דקות)
- הגבלת תור (מקסימום 3 pending בו-זמנית)
- ניקוי משימות תקועות (working > 30 דקות)
- הגנת כפילויות (לא מגיבים פעמיים לאותו post_url)
- מגבלה יומית לפי קטגוריה
- מגבלת באצ' (1 תגובה למחזור)
"""
import asyncio
import random
from datetime import datetime, timedelta, timezone
from loguru import logger
from sqlalchemy import select, and_, func, or_

from app.database import get_async_session_context
from app.models.lead_hunter import LeadPost, LeadCategory, LeadArea

LEAD_REPLY_QUEUE_INTERVAL = 180  # 3 דקות
MAX_PER_BATCH = 1
MAX_POST_AGE_HOURS = 48
MAX_PENDING_TASKS = 3
MIN_GAP_BETWEEN_REPLIES_MIN = 8
MAX_GAP_BETWEEN_REPLIES_MIN = 15
STUCK_TASK_TIMEOUT_MINUTES = 30
ACTIVE_HOUR_START = 7   # 07:00 שעון ישראל
ACTIVE_HOUR_END = 22    # 22:00 שעון ישראל
ISRAEL_UTC_OFFSET = 2   # UTC+2 (חורף), לעדכן ל-3 בקיץ


def _is_active_hours() -> bool:
    """בדיקה אם אנחנו בחלון שעות הפעילות (שעון ישראל)."""
    utc_now = datetime.utcnow()
    israel_hour = (utc_now.hour + ISRAEL_UTC_OFFSET) % 24
    return ACTIVE_HOUR_START <= israel_hour < ACTIVE_HOUR_END


async def _cleanup_stuck_tasks(session) -> int:
    """ניקוי משימות שנתקעו בסטטוס working יותר מ-30 דקות."""
    stuck_cutoff = datetime.utcnow() - timedelta(minutes=STUCK_TASK_TIMEOUT_MINUTES)
    stuck_result = await session.execute(
        select(LeadPost).where(
            and_(
                LeadPost.auto_reply_status == "working",
                LeadPost.updated_at <= stuck_cutoff,
            )
        )
    )
    stuck_posts = stuck_result.scalars().all()

    for post in stuck_posts:
        post.auto_reply_status = "failed"
        logger.warning(
            f"🎯 ⏰ Lead Hunter: post {post.id} stuck in 'working' for >{STUCK_TASK_TIMEOUT_MINUTES}min, "
            f"marked as failed (url={post.post_url})"
        )

    return len(stuck_posts)


async def _count_pending_tasks(session) -> int:
    """ספירת משימות pending שמחכות לתוסף Chrome."""
    result = await session.execute(
        select(func.count(LeadPost.id)).where(
            LeadPost.auto_reply_status.in_(["pending", "working"])
        )
    )
    return result.scalar_one() or 0


async def _get_last_reply_time(session) -> datetime | None:
    """מציאת הזמן של התגובה האחרונה שנשלחה."""
    result = await session.execute(
        select(LeadPost.auto_reply_sent_at)
        .where(
            and_(
                LeadPost.auto_reply_sent == True,
                LeadPost.auto_reply_sent_at.isnot(None),
            )
        )
        .order_by(LeadPost.auto_reply_sent_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _is_duplicate_url(session, post_url: str) -> bool:
    """בדיקה אם כבר נשלחה תגובה לאותו post_url."""
    result = await session.execute(
        select(func.count(LeadPost.id)).where(
            and_(
                LeadPost.post_url == post_url,
                LeadPost.auto_reply_sent == True,
            )
        )
    )
    count = result.scalar_one() or 0
    return count > 0


async def queue_lead_hunter_replies():
    """
    מוצאת פוסטים מתאימים לתגובה אוטומטית ומסמנת אותם כ-pending לתוסף Chrome.
    כוללת את כל הגנות הבטיחות.
    """
    try:
        async with get_async_session_context() as session:

            # --- הגנה 1: שעות פעילות ---
            if not _is_active_hours():
                utc_now = datetime.utcnow()
                israel_hour = (utc_now.hour + ISRAEL_UTC_OFFSET) % 24
                logger.debug(
                    f"🎯 🕐 Lead Hunter: outside active hours "
                    f"(Israel time: {israel_hour:02d}:00, window: {ACTIVE_HOUR_START:02d}:00-{ACTIVE_HOUR_END:02d}:00)"
                )
                return

            # --- ניקוי משימות תקועות ---
            stuck_count = await _cleanup_stuck_tasks(session)
            if stuck_count > 0:
                logger.info(f"🎯 🧹 Lead Hunter: cleaned {stuck_count} stuck tasks")
                await session.commit()

            # --- הגנה 2: הגבלת תור ---
            pending_count = await _count_pending_tasks(session)
            if pending_count >= MAX_PENDING_TASKS:
                logger.info(
                    f"🎯 ⏸️ Lead Hunter: {pending_count} tasks already pending/working "
                    f"(max={MAX_PENDING_TASKS}), skipping this cycle"
                )
                return

            # --- הגנה 3: מרווח מינימלי בין תגובות ---
            last_reply_time = await _get_last_reply_time(session)
            if last_reply_time:
                min_gap = timedelta(minutes=MIN_GAP_BETWEEN_REPLIES_MIN)
                time_since_last = datetime.utcnow() - last_reply_time
                if time_since_last < min_gap:
                    remaining = min_gap - time_since_last
                    logger.debug(
                        f"🎯 ⏳ Lead Hunter: last reply was {time_since_last.total_seconds():.0f}s ago, "
                        f"minimum gap is {MIN_GAP_BETWEEN_REPLIES_MIN}min, "
                        f"waiting {remaining.total_seconds():.0f}s more"
                    )
                    return

            # --- קטגוריות פעילות ---
            categories_result = await session.execute(
                select(LeadCategory).where(
                    and_(
                        LeadCategory.auto_reply_enabled == True,
                        LeadCategory.is_active == True,
                    )
                )
            )
            categories = categories_result.scalars().all()

            if not categories:
                return

            logger.debug(
                f"🎯 Lead Hunter: checking {len(categories)} active categories "
                f"(pending={pending_count}, max_pending={MAX_PENDING_TASKS})"
            )

            areas_result = await session.execute(select(LeadArea))
            areas = {a.name: a for a in areas_result.scalars().all()}

            total_queued = 0

            for category in categories:
                delay_minutes = category.auto_reply_delay_minutes or 10
                daily_limit = category.auto_reply_daily_limit or 10
                cutoff = datetime.utcnow() - timedelta(minutes=delay_minutes)
                max_age_cutoff = datetime.utcnow() - timedelta(hours=MAX_POST_AGE_HOURS)

                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                sent_today_result = await session.execute(
                    select(func.count(LeadPost.id)).where(
                        and_(
                            LeadPost.category_id == category.id,
                            LeadPost.auto_reply_sent == True,
                            LeadPost.auto_reply_sent_at >= today_start,
                        )
                    )
                )
                sent_today = sent_today_result.scalar_one() or 0

                if sent_today >= daily_limit:
                    logger.info(
                        f"🎯 📊 Lead Hunter: category '{category.name}' "
                        f"daily limit reached ({sent_today}/{daily_limit})"
                    )
                    continue

                remaining = daily_limit - sent_today
                batch_limit = min(MAX_PER_BATCH, remaining)

                eligible_result = await session.execute(
                    select(LeadPost).where(
                        and_(
                            LeadPost.category_id == category.id,
                            LeadPost.ai_reply.isnot(None),
                            LeadPost.ai_reply != "",
                            LeadPost.auto_reply_sent == False,
                            LeadPost.auto_reply_status.is_(None),
                            LeadPost.status.in_(["classified", "notified"]),
                            LeadPost.created_at <= cutoff,
                            LeadPost.created_at >= max_age_cutoff,
                        )
                    ).order_by(LeadPost.created_at.asc()).limit(batch_limit)
                )
                eligible_posts = eligible_result.scalars().all()

                logger.debug(
                    f"🎯 Lead Hunter: category '{category.name}' - "
                    f"sent_today={sent_today}/{daily_limit}, "
                    f"eligible={len(eligible_posts)}, batch_limit={batch_limit}"
                )

                for post in eligible_posts:
                    # בדיקת אזור
                    area = areas.get(post.area)
                    if area and not area.is_reply_enabled:
                        logger.debug(
                            f"🎯 Lead Hunter: skipping post {post.id} - "
                            f"area '{post.area}' reply disabled"
                        )
                        continue

                    # --- הגנה 4: כפילויות ---
                    if await _is_duplicate_url(session, post.post_url):
                        post.auto_reply_status = "skipped"
                        logger.warning(
                            f"🎯 🔁 Lead Hunter: skipping post {post.id} - "
                            f"duplicate URL already replied: {post.post_url}"
                        )
                        continue

                    # --- סימון pending ---
                    post.auto_reply_status = "pending"
                    total_queued += 1
                    logger.info(
                        f"🎯 ✅ Lead Hunter: queued post {post.id} for auto-reply "
                        f"(category='{category.name}', area='{post.area}', "
                        f"url={post.post_url})"
                    )

                    # רק תגובה אחת למחזור
                    if total_queued >= MAX_PER_BATCH:
                        break

                if total_queued >= MAX_PER_BATCH:
                    break

            if total_queued > 0:
                await session.commit()
                logger.info(
                    f"🎯 Lead Hunter: {total_queued} post(s) queued for Chrome extension "
                    f"(pending_total={pending_count + total_queued})"
                )
            else:
                await session.commit()

    except Exception as e:
        logger.error(f"🎯 ❌ Lead Hunter queue task error: {e}", exc_info=True)


async def start_lead_hunter_reply_task():
    logger.info(
        f"🎯 Lead Hunter Auto-Reply Task started "
        f"(batch={MAX_PER_BATCH}, max_pending={MAX_PENDING_TASKS}, "
        f"gap={MIN_GAP_BETWEEN_REPLIES_MIN}-{MAX_GAP_BETWEEN_REPLIES_MIN}min, "
        f"hours={ACTIVE_HOUR_START:02d}:00-{ACTIVE_HOUR_END:02d}:00 IL, "
        f"stuck_timeout={STUCK_TASK_TIMEOUT_MINUTES}min)"
    )

    while True:
        try:
            await queue_lead_hunter_replies()
        except Exception as e:
            logger.error(f"🎯 Lead Hunter reply task error: {e}", exc_info=True)

        jitter = random.randint(0, 30)
        await asyncio.sleep(LEAD_REPLY_QUEUE_INTERVAL + jitter)
