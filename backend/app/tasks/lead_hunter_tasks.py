"""
PartnerCalc OS - Lead Hunter Auto-Reply Tasks
משימות רקע לתגובה אוטומטית על פוסטים שנקלטו מפושר

הגנות בטיחות מפני חסימות פייסבוק:
- חלון שעות פעילות (07:00-23:00 שעון ישראל)
- מגבלה יומית דינמית (עולה בהדרגה לפי ימים פעילים)
- עדיפות לאזור מרכז
- מרווח מינימלי בין תגובות (8-15 דקות)
- הגבלת תור (מקסימום 3 pending בו-זמנית)
- ניקוי משימות תקועות (working > 30 דקות)
- הגנת כפילויות (לא מגיבים פעמיים לאותו post_url)
- מגבלת באצ' (1 תגובה למחזור)
- התראת WhatsApp כש-Brave לא פעיל
"""
import asyncio
import hashlib
import random
from datetime import datetime, timedelta, timezone
from loguru import logger
from sqlalchemy import select, and_, func, case, or_

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
ACTIVE_HOUR_END = 23    # 23:00 שעון ישראל
ISRAEL_UTC_OFFSET = 3   # UTC+3 (קיץ IDT). לעדכן ל-2 בחורף (אחרי אוקטובר)
PRIORITY_AREA = "מרכז"
BLOCKED_GROUPS = [
    "1629283237109586",  # הובלות, מובילים ממומלצים, חיפוש מובילים
    "BeerShevaTogether",  # באר שבע ביחד
    "186182019096864",  # דלתות פנים במחירי חיסול
]
BRAVE_ALERT_PHONE = "0542575412"
BRAVE_STUCK_ALERT_MINUTES = 20  # אם pending תקוע 20 דק = Brave לא פעיל
APPROVAL_PHONE = "0542575412"
REQUIRE_WHATSAPP_APPROVAL = False  # True = ממתין לאישור WhatsApp. False = פרסום אוטומטי + הודעה לסקירה
SEND_WHATSAPP_NOTIFICATION = True  # True = שולח הודעת WhatsApp לסקירה (לא חוסם פרסום)
PHONE_REPLIES_PER_DAY = 1  # כמה תגובות עם טלפון ביום (0 = כבוי)
PHONE_NUMBER = "053-7934107"  # הטלפון של הובלות בישראל

# מגבלה יומית הדרגתית -- מספר אקראי-יציב שמשתנה כל יום
DAILY_LIMIT_SCHEDULE = [
    (1, 7, 3, 5),       # שבוע 1: 3-5 ביום
    (8, 14, 5, 10),     # שבוע 2: 5-10 ביום
    (15, 999, 8, 15),   # שבוע 3+: 8-15 ביום
]


def _get_dynamic_daily_limit(activation_date: datetime | None) -> int:
    """
    מחשב מגבלה יומית דינמית לפי מספר הימים מאז ההפעלה.
    המגבלה עולה בהדרגה ומשתנה באופן אקראי-יציב (אותו ערך לאותו יום).
    """
    if not activation_date:
        return 5

    days_active = (datetime.utcnow() - activation_date).days + 1

    for start_day, end_day, min_limit, max_limit in DAILY_LIMIT_SCHEDULE:
        if start_day <= days_active <= end_day:
            # seed אקראי-יציב לפי התאריך (אותו מספר לאותו יום)
            date_seed = datetime.utcnow().strftime("%Y-%m-%d")
            seed = int(hashlib.md5(date_seed.encode()).hexdigest()[:8], 16)
            rng = random.Random(seed)
            limit = rng.randint(min_limit, max_limit)
            logger.debug(
                f"🎯 📈 Lead Hunter: day {days_active} -> daily limit={limit} "
                f"(range {min_limit}-{max_limit})"
            )
            return limit

    return 5


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


async def _check_brave_and_alert(session):
    """
    אם יש משימה pending שלא נלקחה מעל 20 דקות = Brave לא פעיל.
    שולח התראת WhatsApp פעם אחת (לא ספאם).
    """
    alert_cutoff = datetime.utcnow() - timedelta(minutes=BRAVE_STUCK_ALERT_MINUTES)
    result = await session.execute(
        select(LeadPost).where(
            and_(
                LeadPost.auto_reply_status == "pending",
                LeadPost.updated_at <= alert_cutoff,
            )
        ).limit(1)
    )
    stuck_pending = result.scalar_one_or_none()

    if not stuck_pending:
        return

    from app.services.whatsapp_service import get_whatsapp_service
    ws = get_whatsapp_service()

    if not ws.is_configured:
        logger.warning("🎯 ⚠️ Lead Hunter: Brave appears down but WhatsApp not configured")
        return

    # בדיקה שלא שלחנו התראה בשעה האחרונה (למנוע ספאם)
    cache_key = f"brave_alert_{datetime.utcnow().strftime('%Y-%m-%d-%H')}"
    if getattr(_check_brave_and_alert, '_last_alert', None) == cache_key:
        return

    logger.warning(
        f"🎯 🚨 Lead Hunter: Brave appears down! "
        f"Post {stuck_pending.id} pending for >{BRAVE_STUCK_ALERT_MINUTES}min. "
        f"Sending WhatsApp alert to {BRAVE_ALERT_PHONE}"
    )

    try:
        await ws.send_to_phone(
            BRAVE_ALERT_PHONE,
            f"⚠️ *Lead Hunter - Brave לא פעיל*\n\n"
            f"יש משימת תגובה (post {stuck_pending.id}) שממתינה כבר "
            f"{BRAVE_STUCK_ALERT_MINUTES} דקות.\n"
            f"נא לוודא ש-Brave פתוח עם התוסף פעיל."
        )
        _check_brave_and_alert._last_alert = cache_key
    except Exception as e:
        logger.error(f"🎯 ❌ Failed to send Brave alert WhatsApp: {e}")


async def _count_pending_tasks(session) -> int:
    """ספירת משימות בתהליך: awaiting_approval + pending + working."""
    result = await session.execute(
        select(func.count(LeadPost.id)).where(
            LeadPost.auto_reply_status.in_(["awaiting_approval", "pending", "working"])
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


async def _send_approval_whatsapp(post: LeadPost, category: LeadCategory):
    """שליחת הודעת WhatsApp לאישור תגובה אוטומטית."""
    from app.services.whatsapp_service import get_whatsapp_service
    ws = get_whatsapp_service()

    if not ws.is_configured:
        logger.warning(f"🎯 ⚠️ Lead Hunter: WhatsApp not configured, cannot send approval for post {post.id}")
        return

    desc_preview = (post.description or "")[:200]
    if len(post.description or "") > 200:
        desc_preview += "..."

    reply_preview = (post.ai_reply or "")[:300]
    if len(post.ai_reply or "") > 300:
        reply_preview += "..."

    message = (
        f"🎯 *אישור תגובה אוטומטית*\n\n"
        f"📋 פוסט #{post.id}\n"
        f"📁 {post.group_name or 'קבוצה לא ידועה'}\n"
        f"📍 אזור: {post.area or 'לא ידוע'}\n\n"
        f"📝 *הפוסט:*\n{desc_preview}\n\n"
        f"💬 *תגובה מוצעת:*\n{reply_preview}\n\n"
        f"✅ השב *1* לאישור פרסום\n"
        f"❌ השב *0* לדחייה"
    )

    try:
        result = await ws.send_to_phone(APPROVAL_PHONE, message)
        if result.get("success"):
            logger.info(f"🎯 📩 Lead Hunter: approval WhatsApp sent for post {post.id}")
        else:
            logger.error(f"🎯 ❌ Lead Hunter: failed to send approval WhatsApp for post {post.id}: {result.get('error')}")
    except Exception as e:
        logger.error(f"🎯 ❌ Lead Hunter: approval WhatsApp exception for post {post.id}: {e}")


async def _send_notification_whatsapp(post: LeadPost, category: LeadCategory):
    """שליחת הודעת WhatsApp אינפורמטיבית (לסקירה בלבד, לא חוסמת פרסום)."""
    from app.services.whatsapp_service import get_whatsapp_service
    ws = get_whatsapp_service()

    if not ws.is_configured:
        return

    desc_preview = (post.description or "")[:200]
    if len(post.description or "") > 200:
        desc_preview += "..."

    reply_preview = (post.ai_reply or "")[:300]
    if len(post.ai_reply or "") > 300:
        reply_preview += "..."

    message = (
        f"🎯 *תגובה פורסמה אוטומטית*\n\n"
        f"📋 פוסט #{post.id}\n"
        f"📁 {post.group_name or 'קבוצה לא ידועה'}\n"
        f"📍 אזור: {post.area or 'לא ידוע'}\n\n"
        f"📝 *הפוסט:*\n{desc_preview}\n\n"
        f"💬 *תגובה שפורסמה:*\n{reply_preview}\n\n"
        f"🔗 {post.post_url}"
    )

    try:
        await ws.send_to_phone(APPROVAL_PHONE, message)
        logger.info(f"🎯 📩 Lead Hunter: notification WhatsApp sent for post {post.id}")
    except Exception as e:
        logger.error(f"🎯 ❌ Lead Hunter: notification WhatsApp exception for post {post.id}: {e}")


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

            # --- התראת Brave ---
            await _check_brave_and_alert(session)

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
                random_gap = random.randint(MIN_GAP_BETWEEN_REPLIES_MIN, MAX_GAP_BETWEEN_REPLIES_MIN)
                min_gap = timedelta(minutes=random_gap)
                time_since_last = datetime.utcnow() - last_reply_time
                if time_since_last < min_gap:
                    remaining = min_gap - time_since_last
                    logger.debug(
                        f"🎯 ⏳ Lead Hunter: last reply was {time_since_last.total_seconds():.0f}s ago, "
                        f"random gap is {random_gap}min, "
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
                cutoff = datetime.utcnow() - timedelta(minutes=delay_minutes)
                max_age_cutoff = datetime.utcnow() - timedelta(hours=MAX_POST_AGE_HOURS)

                # --- מגבלה יומית דינמית ---
                daily_limit = _get_dynamic_daily_limit(category.updated_at)

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

                # --- שליפת פוסטים עם עדיפות לאזור מרכז ---
                area_priority = case(
                    (LeadPost.area == PRIORITY_AREA, 0),
                    else_=1,
                )

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
                    ).order_by(area_priority, LeadPost.created_at.asc()).limit(batch_limit)
                )
                eligible_posts = eligible_result.scalars().all()

                logger.debug(
                    f"🎯 Lead Hunter: category '{category.name}' - "
                    f"sent_today={sent_today}/{daily_limit}, "
                    f"eligible={len(eligible_posts)}, batch_limit={batch_limit}"
                )

                for post in eligible_posts:
                    # --- הגנה: קבוצות חסומות ---
                    if any(gid in (post.group_url or "") or gid in (post.post_url or "") for gid in BLOCKED_GROUPS):
                        post.auto_reply_status = "group_blocked"
                        logger.info(
                            f"🎯 🚫 Lead Hunter: skipping post {post.id} - "
                            f"blocked group: {post.group_name}"
                        )
                        continue

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

                    # --- ניסיון טלפון: תגובה 1 ביום עם מספר טלפון ---
                    if PHONE_REPLIES_PER_DAY > 0 and sent_today == 0 and post.ai_reply:
                        phone_today_result = await session.execute(
                            select(func.count(LeadPost.id)).where(
                                and_(
                                    LeadPost.auto_reply_sent == True,
                                    LeadPost.auto_reply_sent_at >= today_start,
                                    LeadPost.ai_reply.like(f"%{PHONE_NUMBER}%"),
                                )
                            )
                        )
                        phone_today = phone_today_result.scalar_one() or 0
                        if phone_today < PHONE_REPLIES_PER_DAY:
                            post.ai_reply = post.ai_reply.replace("הובלות בישראל", f"הובלות בישראל {PHONE_NUMBER}")
                            logger.info(f"🎯 📞 Lead Hunter: added phone to post {post.id} ({phone_today+1}/{PHONE_REPLIES_PER_DAY})")

                    # --- סימון לפרסום ---
                    if REQUIRE_WHATSAPP_APPROVAL:
                        post.auto_reply_status = "awaiting_approval"
                        total_queued += 1
                        logger.info(
                            f"🎯 📩 Lead Hunter: post {post.id} awaiting WhatsApp approval "
                            f"(category='{category.name}', area='{post.area}', "
                            f"sent_today={sent_today}/{daily_limit}, "
                            f"url={post.post_url})"
                        )
                        await session.flush()
                        await _send_approval_whatsapp(post, category)
                    else:
                        post.auto_reply_status = "pending"
                        total_queued += 1
                        logger.info(
                            f"🎯 ✅ Lead Hunter: queued post {post.id} for auto-reply "
                            f"(category='{category.name}', area='{post.area}', "
                            f"sent_today={sent_today}/{daily_limit}, "
                            f"url={post.post_url})"
                        )
                        if SEND_WHATSAPP_NOTIFICATION:
                            await session.flush()
                            await _send_notification_whatsapp(post, category)

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
        f"stuck_timeout={STUCK_TASK_TIMEOUT_MINUTES}min, "
        f"priority_area='{PRIORITY_AREA}', "
        f"brave_alert_phone={BRAVE_ALERT_PHONE}, "
        f"whatsapp_approval={'ON' if REQUIRE_WHATSAPP_APPROVAL else 'OFF'}, "
        f"whatsapp_notify={'ON' if SEND_WHATSAPP_NOTIFICATION else 'OFF'})"
    )

    while True:
        try:
            await queue_lead_hunter_replies()
        except Exception as e:
            logger.error(f"🎯 Lead Hunter reply task error: {e}", exc_info=True)

        jitter = random.randint(0, 30)
        await asyncio.sleep(LEAD_REPLY_QUEUE_INTERVAL + jitter)
