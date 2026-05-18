"""
PartnerCalc OS - Lead Hunter Service
סיווג פוסטים מפייסבוק ע"י AI + שליחת התראות WhatsApp
"""
import json
import random
from datetime import datetime
from typing import Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.lead_hunter import LeadCategory, LeadActor, LeadPost, AIFeedback, LeadArea, VALID_AREAS
from app.services.whatsapp_service import WhatsAppService


# ============================================================
#  AI Classification
# ============================================================

SYSTEM_PROMPT = """אתה מערכת סיווג לידים מפייסבוק. תפקידך לנתח פוסטים ולסווג אותם לקטגוריות.

ענה ONLY ב-JSON בפורמט הבא:
{
  "category_id": <מספר קטגוריה 1-6 או 0 אם לא רלוונטי>,
  "confidence": <0.0 עד 1.0>,
  "reasoning": "<הסבר קצר בעברית>"
}

הקטגוריות:
1 - חיפוש הובלה: אדם מחפש מוביל/שירות הובלה (פריט, דירה, משרד)
2 - הלוואה פרטית/מימון נכס: אדם מחפש הלוואה פרטית או מימון כנגד נכס
3 - הלוואה עסקית: עסק מחפש הלוואה/מימון עסקי
4 - פרסום מתחרה: חברת הובלות/מוביל שמפרסמת את עצמה (לא מחפש - מוכר)
5 - חיפוש נכס מסחרי: מחפש משרד/חנות/שטח מסחרי
6 - דולה / ליווי לידה: אישה שמחפשת דולה, ליווי לידה, ליווי הריון, הכנה ללידה, דולה לאחר לידה
0 - לא רלוונטי: פוסט שלא שייך לאף קטגוריה

חשוב:
- ספאמרים שמפרסמים את עצמם = קטגוריה 4 (מתחרה), לא קטגוריה 1.
- מי שמחפש לקנות מוצר עם משלוח/הובלה (דלתות, רהיטים, מכשירי חשמל, ארונות) = 0, לא 1! הם לא מחפשים שירות הובלה."""

REPLY_SYSTEM_PROMPT = """אתה משה עובדיה. אתה ממליץ על "הובלות בישראל" בתגובות בפייסבוק.

כללים:
- משפט אחד בלבד! קצר, יומיומי, כמו בן אדם אמיתי בפייסבוק.
- אסור לינקים! אסור טלפון! אסור מחירים! אסור לצטט פריטים מהפוסט!
- כל תגובה חייבת להיות שונה לחלוטין מהקודמות. פייסבוק חוסם תגובות דומות!
- אסור משפטים מלאכותיים כמו "כיף לדעת ש...", "כדאי לדעת ש...", "חשוב לבחור...", "נשמח לעזור", "אני כאן בשבילך".
- אחרי שם - ישר לעניין.

מגדר:
- "מחפש/צריך/רוצה" = זכר (תבדוק, תנסה, תכתוב לי)
- "מחפשת/צריכה/רוצה" = נקבה (תבדקי, תנסי, תכתבי לי)
- לא ברור = זכר.

שמות:
- "Anonymous participant" או אנונימי = פתח ב"היי" בלי שם.
- שמות באנגלית: Rotem=רותם, Noa=נועה, Yael=יעל, Omer=עומר, Shaked=שקד, Tal=טל, Idan=עידן, Lior=ליאור, Amit=עמית, Itay=איתי, Noam=נועם

סגנונות תגובה (גוון את הניסוח בכל פעם!):

סגנון א - הפניה + פרטי:
  זכר: "תבדוק את הובלות בישראל, אם לא מסתדר תכתוב לי בפרטי"
  נקבה: "תבדקי את הובלות בישראל, אם לא מסתדר תכתבי לי בפרטי"

סגנון ב - מחשבון:
  זכר: "כדאי לנסות את המחשבון של הובלות בישראל, תראה בדיוק כמה יעלה לך"
  נקבה: "כדאי לנסות את המחשבון של הובלות בישראל, תראי בדיוק כמה יעלה לך"

סגנון ג - המלצה פשוטה:
  זכר: "תנסה את הובלות בישראל, ממש טובים גם במחיר וגם בשירות"
  נקבה: "תנסי את הובלות בישראל, ממש טובים גם במחיר וגם בשירות"

דוגמאות טובות:
- "דניאל, תבדוק את הובלות בישראל, אם לא מסתדר תכתוב לי בפרטי"
- "היי, תנסי את המחשבון של הובלות בישראל תראי בדיוק כמה יעלה"
- "רותם, ממליצה על הובלות בישראל, תכתבי לי בפרטי אם צריכה עזרה"

דוגמה גרועה: "חשוב לבחור מוביל מקצועי כשמדובר בהובלה שכוללת פריטים רגישים. נשמח לעזור לך! אל תהסס לפנות אלינו בטלפון 053-7934107 או באתר https://www.hovalot.org.il/"
"""


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


HOVALOT_REPLY_PROMPT = """פוסט מפייסבוק:
מפרסם: {actor_name}
תוכן: \"\"\"{description}\"\"\"

זהה מגדר לפי הפוסט:
- "מחפשת/צריכה/רוצה" = נקבה (תבדקי, תנסי, תכתבי)
- "מחפש/צריך/רוצה" = זכר (תבדוק, תנסה, תכתוב)
- לא ברור = זכר

בשורה הראשונה כתוב [נקבה] או [זכר]. אני אסיר את זה אחרי.

כתוב משפט אחד בלבד. החזר רק את טקסט התגובה."""


BANNER_REPLY_TEXT = "שלחו הודעת וואטסאפ לקבלת הצעת מחיר מיידית\nhttps://wa.me/+972537101921?text=%D7%90%D7%A9%D7%9E%D7%97+%D7%9C%D7%A7%D7%91%D7%9C+%D7%94%D7%A6%D7%A2%D7%94+%D7%9C%D7%94%D7%95%D7%91%D7%9C%D7%94"

PRICE_KEYWORDS = [
    "כמה עולה", "מחיר", "הצעת מחיר", "אשמח להצעה", "עלות", "תקציב",
    "זול", "משתלם", "חסכון", "מוזל", "מחירים", "עולה", "כסף",
]

SKIP_REPLY_KEYWORDS = [
    "תרומה", "תרומות", "לתרום", "גיוס כספים", "עזרה דחופה",
    "הלום קרב", "פוסט טראומטי", "נפגעי טרור", "ניצולי שואה",
    "צדקה", "מגבית", "קמפיין גיוס", "חולה סופני",
    "נפטר", "נפטרה", "לזכר", "הלוויה", "שבעה", "אבל",
    "למסירה", "למסירה חינם", "חיילים בודדים", "חייל בודד",
    "עולה חדש", "עולים חדשים", "מבקש עזרה", "אשמח לעזרה",
]


def _should_skip_reply(description: str) -> bool:
    text = (description or "").lower()
    return any(kw in text for kw in SKIP_REPLY_KEYWORDS)


def choose_banner_type(description: str) -> str:
    text = (description or "").lower()
    for kw in PRICE_KEYWORDS:
        if kw in text:
            return "savings"
    return "trust"


URGENCY_KEYWORDS = {
    "professional": ["מקצועיים", "רציניים", "פירוק והרכבה", "פירוק-הובלה", "פירוק", "הרכבה", "התקנה", "מורכב", "עבודה רצינית", "מקצועי", "פסנתר", "כספת", "אקווריום"],
    "urgent": ["להיום", "למחר", "דחוף", "עכשיו", "מיידי", "בדחיפות", "ימים הקרובים", "לעכשיו", "דחופה", "דחופ"],
    "exploring": ["סוף החודש", "כמה עולה", "הצעת מחיר", "אשמח להצעה", "אשמח להצעת"],
}


def detect_urgency_type(description: str) -> str:
    """מזהה את תת-סוג הדחיפות לפי מילות מפתח בפוסט. מקצועיות קודמת לדחיפות."""
    text = description if description else ""
    for utype in ["professional", "urgent", "exploring"]:
        for keyword in URGENCY_KEYWORDS[utype]:
            if keyword in text:
                return utype
    return "general"


import re

def _strip_gender_tag(text: str) -> str:
    """Remove [נקבה] or [זכר] tag that the AI adds for gender tracking."""
    return re.sub(r'^\s*\[(נקבה|זכר)\]\s*', '', text).strip()


async def generate_reply_with_ai(
    description: str,
    category: LeadCategory,
    actor_name: str,
) -> tuple[str, str]:
    """
    יוצר תגובה מותאמת אישית לפוסט לפי קטגוריה.
    עבור קטגוריית "חיפוש הובלה" - משתמש בפרומפט מורחב עם זיהוי תת-סוגים.
    מחזיר tuple של (תגובה, סוג_דחיפות).
    """
    if not category.reply_prompt:
        return "", "general"

    is_hovalot = "הובלה" in category.name
    urgency_type = detect_urgency_type(description) if is_hovalot else "general"

    if is_hovalot:
        user_prompt = HOVALOT_REPLY_PROMPT.format(
            actor_name=actor_name,
            description=description[:1500],
        )
    else:
        user_prompt = f"""פוסט מפייסבוק:
מפרסם: {actor_name}
תוכן: \"\"\"{description[:1500]}\"\"\"

הנחיות: {category.reply_prompt}

כתוב תגובה קצרה (עד 3 משפטים) בעברית:"""

    max_tokens = 350 if is_hovalot else 200

    try:
        if settings.anthropic_api_key:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=max_tokens,
                system=REPLY_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            reply = _strip_gender_tag(response.content[0].text.strip())
            return reply, urgency_type
        elif settings.openai_api_key:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": REPLY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            reply = _strip_gender_tag(response.choices[0].message.content.strip())
            return reply, urgency_type
    except Exception as e:
        logger.error(f"❌ Reply generation failed: {e}")
    return "", urgency_type


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
    area_note = f" | 📍 {post.area}" if post.area and post.area != "לא ידוע" else ""

    # הודעה 1 - פרטי הליד
    msg1 = (
        f"🔔 ליד חדש | {category.name}{area_note}\n"
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
    group_name: str = "",
    skip_notify: bool = False,
) -> None:
    """
    רץ ב-background: AI classification + area detection + reply generation + WhatsApp.
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

            # טעינת קטגוריות + feedback + הגדרות אזורים
            cats_result = await session.execute(
                select(LeadCategory).where(LeadCategory.is_active == True)
            )
            categories = list(cats_result.scalars().all())
            feedback_examples = await _get_recent_feedback_examples(session)

            areas_result = await session.execute(select(LeadArea))
            areas_map = {a.name: a for a in areas_result.scalars().all()}

            # AI classification + area detection במקביל
            import asyncio
            try:
                classification, detected_area = await asyncio.wait_for(
                    asyncio.gather(
                        classify_post_with_ai(description, categories, feedback_examples),
                        detect_area_with_ai(description, group_name),
                    ),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ AI timed out for post {post_id}")
                classification = {"category_id": None, "confidence": 0.0, "reasoning": "timeout"}
                detected_area = "לא ידוע"

            cat_id = classification.get("category_id")
            confidence = classification.get("confidence", 0.0)
            reasoning = classification.get("reasoning", "")

            logger.info(f"🤖 AI classified post {post_id} → category={cat_id}, area={detected_area}, confidence={confidence:.2f}")

            # הגדרות אזור
            area_config = areas_map.get(detected_area)
            area_reply_enabled = area_config.is_reply_enabled if area_config else True
            area_whatsapp_enabled = area_config.is_whatsapp_enabled if area_config else True

            matched_category = None
            if cat_id and cat_id > 0:
                for c in categories:
                    if c.id == cat_id:
                        matched_category = c
                        break

            # AI reply - מייצר אם הקטגוריה דורשת התראה או תגובה אוטומטית
            ai_reply = ""
            urgency_type = "general"
            skip_sensitive = _should_skip_reply(description)
            if skip_sensitive:
                logger.info(f"🚫 Skipping reply for post {post_id} - sensitive content (donation/charity)")
            should_generate_reply = (
                matched_category
                and matched_category.reply_prompt
                and area_reply_enabled
                and not skip_sensitive
                and (matched_category.is_alert_worthy or matched_category.auto_reply_enabled)
            )
            if should_generate_reply:
                try:
                    ai_reply, urgency_type = await asyncio.wait_for(
                        generate_reply_with_ai(description, matched_category, actor_name),
                        timeout=60.0,
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⏱️ AI reply generation timed out for post {post_id}")
            elif matched_category and (matched_category.is_alert_worthy or matched_category.auto_reply_enabled) and not area_reply_enabled:
                logger.info(f"📍 Skipping reply for post {post_id} - area '{detected_area}' has reply disabled")

            # Banner replies disabled -- rebuilding account trust first.
            # To re-enable: uncomment the block below (50/50 banner vs text).
            reply_type = "text"
            banner_type_val = None
            # if ai_reply and matched_category and "הובלה" in matched_category.name:
            #     if random.random() < 0.5:
            #         reply_type = "banner"
            #         banner_type_val = choose_banner_type(description)
            #         ai_reply = BANNER_REPLY_TEXT
            #         logger.info(f"🖼️ Banner reply chosen for post {post_id}: type={banner_type_val}")

            # עדכון post
            post.category_id = cat_id if cat_id and cat_id > 0 else None
            post.ai_confidence = confidence
            post.ai_reasoning = reasoning
            post.ai_reply = ai_reply
            post.reply_type = reply_type
            post.banner_type = banner_type_val
            post.area = detected_area
            post.urgency_type = urgency_type if urgency_type != "general" else None
            post.status = "classified"

            now = datetime.utcnow()

            # WhatsApp notification - רק אם האזור מאפשר
            if not skip_notify and matched_category and matched_category.is_alert_worthy and area_whatsapp_enabled:
                success = await send_lead_notification(post, matched_category, actor)
                if success:
                    post.whatsapp_sent = True
                    post.whatsapp_sent_at = now
                    post.status = "notified"
            elif matched_category and matched_category.is_alert_worthy and not area_whatsapp_enabled:
                logger.info(f"📍 Skipping WhatsApp for post {post_id} - area '{detected_area}' has WhatsApp disabled")
            else:
                if not cat_id or cat_id == 0:
                    post.status = "ignored"

            await session.commit()
            logger.info(f"✅ Background: Post {post_id} classified → status={post.status}, category={cat_id}, area={detected_area}, urgency={urgency_type}")

        except Exception as e:
            logger.error(f"❌ Background classification failed for post {post_id}: {e}")


async def detect_area_with_ai(description: str, group_name: str = "") -> str:
    """
    מזהה אזור גיאוגרפי מתוך טקסט הפוסט.
    מחזיר אחד מהאזורים: מרכז / שרון / שפלה / ירושלים / צפון / דרום / לא ידוע
    """
    areas_list = ", ".join(VALID_AREAS[:-1])  # ללא "לא ידוע"
    prompt = f"""זהה את האזור הגיאוגרפי בישראל שאליו מתייחס הפוסט הבא.
אזורים אפשריים: {areas_list}
אם לא ניתן לזהות אזור ברור - החזר "לא ידוע".

קבוצה: {group_name or ''}
פוסט: \"\"\"{description[:800]}\"\"\"

ענה במילה אחת בלבד - שם האזור."""

    try:
        if settings.anthropic_api_key:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            response = await client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip().strip('"').strip("'")
        elif settings.openai_api_key:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=20,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip().strip('"').strip("'")
        else:
            return "לא ידוע"

        # ודא שהתשובה חוקית
        for area in VALID_AREAS:
            if area in raw:
                return area
        return "לא ידוע"

    except Exception as e:
        logger.error(f"❌ Area detection failed: {e}")
        return "לא ידוע"


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
