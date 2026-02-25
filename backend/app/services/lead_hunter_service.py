"""
PartnerCalc OS - Lead Hunter Service
סיווג פוסטים מפייסבוק ע"י AI + שליחת התראות WhatsApp
"""
import json
from datetime import datetime
from typing import Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.lead_hunter import LeadCategory, LeadActor, LeadPost, AIFeedback
from app.services.whatsapp_service import WhatsAppService


# ============================================================
#  AI Classification
# ============================================================

SYSTEM_PROMPT = """אתה מערכת סיווג לידים מפייסבוק. תפקידך לנתח פוסטים ולסווג אותם לקטגוריות.

ענה ONLY ב-JSON בפורמט הבא:
{
  "category_id": <מספר קטגוריה 1-5 או 0 אם לא רלוונטי>,
  "confidence": <0.0 עד 1.0>,
  "reasoning": "<הסבר קצר בעברית>"
}

הקטגוריות:
1 - חיפוש הובלה: אדם מחפש מוביל/שירות הובלה (פריט, דירה, משרד)
2 - הלוואה פרטית/מימון נכס: אדם מחפש הלוואה פרטית או מימון כנגד נכס
3 - הלוואה עסקית: עסק מחפש הלוואה/מימון עסקי
4 - פרסום מתחרה: חברת הובלות/מוביל שמפרסמת את עצמה (לא מחפש - מוכר)
5 - חיפוש נכס מסחרי: מחפש משרד/חנות/שטח מסחרי
0 - לא רלוונטי: פוסט שלא שייך לאף קטגוריה

חשוב: ספאמרים שמפרסמים את עצמם = קטגוריה 4 (מתחרה), לא קטגוריה 1."""

REPLY_SYSTEM_PROMPT = """אתה כותב תגובות קצרות ומקצועיות לפוסטים בפייסבוק בעברית.
כתוב תגובה אנושית, חמה ומזמינה - לא רובוטית.
עד 3 משפטים. אל תציין מחירים ספציפיים. סיים בהזמנה ליצור קשר."""


async def classify_post_with_ai(
    description: str,
    categories: list[LeadCategory],
    feedback_examples: list[dict] | None = None,
) -> dict:
    """
    מסווג פוסט ע"י AI ומחזיר category_id, confidence, reasoning.
    """
    # בניית הקשר של קטגוריות דינמי מה-DB
    cats_text = "\n".join(
        f"{cat.id} - {cat.name}: {cat.description or ''}" for cat in categories if cat.is_active
    )

    # Negative examples מה-feedback (עד 5 אחרונים)
    negative_section = ""
    if feedback_examples:
        examples = "\n".join(
            f'- "{ex["description"][:100]}..." → טעות: סווג כ-{ex["original"]}, נכון: {ex["corrected"]}'
            for ex in feedback_examples[:5]
        )
        negative_section = f"\n\nדוגמאות לטעויות קודמות (אל תחזור עליהן):\n{examples}"

    user_prompt = f"""סווג את הפוסט הבא:

קטגוריות:
{cats_text}
{negative_section}

פוסט לסיווג:
\"\"\"{description[:2000]}\"\"\"

ענה ב-JSON בלבד."""

    try:
        if settings.anthropic_api_key:
            return await _classify_with_claude(user_prompt)
        elif settings.openai_api_key:
            return await _classify_with_openai(user_prompt)
        else:
            logger.warning("⚠️ No AI API key configured - returning unclassified")
            return {"category_id": None, "confidence": 0.0, "reasoning": "אין מפתח AI"}
    except Exception as e:
        logger.error(f"❌ AI classification failed: {e}")
        return {"category_id": None, "confidence": 0.0, "reasoning": f"שגיאה: {str(e)}"}


async def _classify_with_claude(user_prompt: str) -> dict:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text.strip()
    # נסה לחלץ JSON גם אם יש טקסט נוסף
    if "```" in raw:
        raw = raw.split("```")[1].replace("json", "").strip()
    return json.loads(raw)


async def _classify_with_openai(user_prompt: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)


async def generate_reply_with_ai(
    description: str,
    category: LeadCategory,
    actor_name: str,
) -> str:
    """
    יוצר תגובה מותאמת אישית לפוסט לפי קטגוריה.
    """
    if not category.reply_prompt:
        return ""

    user_prompt = f"""פוסט מפייסבוק:
מפרסם: {actor_name}
תוכן: \"\"\"{description[:1500]}\"\"\"

הנחיות: {category.reply_prompt}

כתוב תגובה קצרה (עד 3 משפטים) בעברית:"""

    try:
        if settings.anthropic_api_key:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                system=REPLY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text.strip()
        elif settings.openai_api_key:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=200,
                messages=[
                    {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"❌ Reply generation failed: {e}")
    return ""


# ============================================================
#  WhatsApp Notifications
# ============================================================

def _truncate(text: str, max_len: int = 150) -> str:
    return text[:max_len] + "..." if len(text) > max_len else text


async def send_lead_notification(
    post: LeadPost,
    category: LeadCategory,
    actor: LeadActor,
) -> bool:
    """
    שולח 2 הודעות WhatsApp:
    1. פרטי הליד + לינק
    2. התגובה המוצעת
    """
    if not category.is_alert_worthy or not category.whatsapp_phone:
        logger.info(f"📱 Skipping WhatsApp - category {category.name} not alertworthy or no phone")
        return False

    wa = WhatsAppService()
    if not wa.is_configured:
        logger.warning("📱 WhatsApp not configured")
        return False

    actor_label = actor.actor_name if actor else "לא ידוע"
    post_count_note = f" ⚠️ ({actor.post_count} פוסטים במערכת)" if actor and actor.post_count > 1 else ""

    # הודעה 1 - פרטי הליד
    msg1 = (
        f"🔔 ליד חדש | {category.name}\n"
        f"👤 {actor_label}{post_count_note}\n"
        f"📝 {_truncate(post.description, 150)}\n"
        f"📍 {post.group_name or 'קבוצה לא ידועה'}\n"
        f"🔗 {post.post_url}"
    )

    result1 = await wa.send_to_phone(category.whatsapp_phone, msg1)

    # הודעה 2 - תגובה מוצעת (רק אם יש)
    if post.ai_reply:
        msg2 = f"💬 תגובה מוצעת:\n{post.ai_reply}"
        await wa.send_to_phone(category.whatsapp_phone, msg2)

    success = result1.get("success", False) if isinstance(result1, dict) else bool(result1)
    if success:
        logger.info(f"📱 ✅ WhatsApp sent for post {post.id} to {category.whatsapp_phone}")
    else:
        error_info = result1.get("error", "unknown") if isinstance(result1, dict) else "failed"
        logger.error(f"📱 ❌ WhatsApp failed for post {post.id}: {error_info}")

    return success


# ============================================================
#  Main ingest pipeline
# ============================================================

async def process_ingest(
    post_url: str,
    description: str,
    posted_at: datetime | None,
    group_name: str,
    group_url: str,
    actor_name: str,
    actor_url: str,
    session: AsyncSession,
    skip_notify: bool = False,
) -> dict:
    """
    שלב 1: שמירת פוסט מיידית ל-DB (מחזיר תוצאה מהר).
    שלב 2: AI classification + WhatsApp ירוצו דרך background task.
    מחזיר: {"status": "created"|"duplicate", "post_id": int|None}
    """

    # 1. בדיקת כפילות
    existing = await session.execute(
        select(LeadPost).where(LeadPost.post_url == post_url)
    )
    if existing.scalar_one_or_none():
        logger.info(f"⏭️ Duplicate post - skipping: {post_url[:80]}")
        return {"status": "duplicate", "post_id": None}

    # 2. UPSERT actor
    actor_result = await session.execute(
        select(LeadActor).where(LeadActor.actor_url == actor_url)
    )
    actor = actor_result.scalar_one_or_none()

    now = datetime.utcnow()
    if actor:
        actor.post_count += 1
        actor.last_activity_at = now
        logger.info(f"👤 Actor updated: {actor_name} (post_count={actor.post_count})")
    else:
        actor = LeadActor(
            actor_url=actor_url,
            actor_name=actor_name,
            post_count=1,
            last_activity_at=now,
        )
        session.add(actor)
        await session.flush()
        logger.info(f"👤 New actor: {actor_name}")

    # 3. INSERT post (status=new) - commit מיידי
    post = LeadPost(
        post_url=post_url,
        description=description,
        posted_at=posted_at,
        group_name=group_name,
        group_url=group_url,
        actor_id=actor.id,
        status="new",
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    logger.info(f"📝 Post saved: id={post.id} - AI will classify in background")

    return {"status": "created", "post_id": post.id, "actor_id": actor.id}


async def classify_and_notify_background(
    post_id: int,
    actor_id: int,
    description: str,
    actor_name: str,
    skip_notify: bool = False,
) -> None:
    """
    רץ ב-background: AI classification + reply generation + WhatsApp.
    """
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        try:
            # טען post ו-actor מחדש
            post_result = await session.execute(select(LeadPost).where(LeadPost.id == post_id))
            post = post_result.scalar_one_or_none()
            actor_result = await session.execute(select(LeadActor).where(LeadActor.id == actor_id))
            actor = actor_result.scalar_one_or_none()

            if not post or not actor:
                logger.error(f"❌ Background task: post {post_id} or actor {actor_id} not found")
                return

            # טעינת קטגוריות + feedback
            cats_result = await session.execute(
                select(LeadCategory).where(LeadCategory.is_active == True)
            )
            categories = list(cats_result.scalars().all())
            feedback_examples = await _get_recent_feedback_examples(session)

            # AI classification עם timeout
            import asyncio
            try:
                classification = await asyncio.wait_for(
                    classify_post_with_ai(description, categories, feedback_examples),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ AI classification timed out for post {post_id}")
                classification = {"category_id": None, "confidence": 0.0, "reasoning": "timeout"}

            cat_id = classification.get("category_id")
            confidence = classification.get("confidence", 0.0)
            reasoning = classification.get("reasoning", "")

            logger.info(f"🤖 AI classified post {post_id} → category={cat_id}, confidence={confidence:.2f}")

            matched_category = None
            if cat_id and cat_id > 0:
                for c in categories:
                    if c.id == cat_id:
                        matched_category = c
                        break

            # AI reply
            ai_reply = ""
            if matched_category and matched_category.is_alert_worthy:
                try:
                    ai_reply = await asyncio.wait_for(
                        generate_reply_with_ai(description, matched_category, actor_name),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ AI reply generation timed out for post {post_id}")

            # עדכון post
            post.category_id = cat_id if cat_id and cat_id > 0 else None
            post.ai_confidence = confidence
            post.ai_reasoning = reasoning
            post.ai_reply = ai_reply
            post.status = "classified"

            now = datetime.utcnow()

            # WhatsApp notification
            if not skip_notify and matched_category and matched_category.is_alert_worthy:
                success = await send_lead_notification(post, matched_category, actor)
                if success:
                    post.whatsapp_sent = True
                    post.whatsapp_sent_at = now
                    post.status = "notified"
            else:
                if not cat_id or cat_id == 0:
                    post.status = "ignored"

            await session.commit()
            logger.info(f"✅ Background: Post {post_id} classified → status={post.status}, category={cat_id}")

        except Exception as e:
            logger.error(f"❌ Background classification failed for post {post_id}: {e}")


async def _get_recent_feedback_examples(session: AsyncSession) -> list[dict]:
    """מחזיר 5 דוגמאות feedback אחרונות לשיפור הפרומפט"""
    try:
        result = await session.execute(
            select(AIFeedback, LeadPost)
            .join(LeadPost, AIFeedback.post_id == LeadPost.id)
            .order_by(AIFeedback.created_at.desc())
            .limit(5)
        )
        rows = result.all()
        return [
            {
                "description": row.LeadPost.description[:200],
                "original": row.AIFeedback.original_category_id,
                "corrected": row.AIFeedback.corrected_category_id or "לא רלוונטי",
            }
            for row in rows
        ]
    except Exception:
        return []
