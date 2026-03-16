"""
PartnerCalc OS - Lead Hunter Auto-Reply Tasks
משימות רקע לתגובה אוטומטית על פוסטים שנקלטו מפושר
"""
import asyncio
import random
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, and_, func

from app.database import get_async_session_context
from app.models.lead_hunter import LeadPost, LeadCategory, LeadArea

LEAD_REPLY_QUEUE_INTERVAL = 180  # 3 דקות
MAX_PER_BATCH = 3
MAX_POST_AGE_HOURS = 48


async def queue_lead_hunter_replies():
    """
    מוצאת פוסטים מתאימים לתגובה אוטומטית ומסמנת אותם כ-pending לתוסף Chrome.
    """
    try:
        async with get_async_session_context() as session:
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
                    logger.debug(f"🎯 Lead Hunter: category '{category.name}' daily limit reached ({sent_today}/{daily_limit})")
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

                for post in eligible_posts:
                    area = areas.get(post.area)
                    if area and not area.is_reply_enabled:
                        logger.debug(f"🎯 Lead Hunter: skipping post {post.id} - area '{post.area}' reply disabled")
                        continue

                    post.auto_reply_status = "pending"
                    total_queued += 1
                    logger.info(f"🎯 Lead Hunter: queued post {post.id} for auto-reply (category={category.name})")

            if total_queued > 0:
                await session.commit()
                logger.info(f"🎯 Lead Hunter: {total_queued} posts queued for Chrome extension")

    except Exception as e:
        logger.error(f"🎯 ❌ Lead Hunter queue task error: {e}")


async def start_lead_hunter_reply_task():
    logger.info("🎯 Lead Hunter Auto-Reply Task started")

    while True:
        try:
            await queue_lead_hunter_replies()
        except Exception as e:
            logger.error(f"🎯 Lead Hunter reply task error: {e}")

        jitter = random.randint(0, 30)
        await asyncio.sleep(LEAD_REPLY_QUEUE_INTERVAL + jitter)
