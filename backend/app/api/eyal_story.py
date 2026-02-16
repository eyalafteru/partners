"""
PartnerCalc OS - Eyal Story API
API endpoints לניהול הסיפור של אייל עובדיה
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.database import get_async_session
from app.models.eyal_story import EyalStory

router = APIRouter()


# ========== Schemas ==========

class EyalStoryUpdate(BaseModel):
    """סכמה לעדכון הסיפור"""
    story_content: str
    forbidden_phrases: Optional[str] = None
    ai_instructions: Optional[str] = None


class EyalStoryResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    story_content: str
    forbidden_phrases: Optional[str]
    ai_instructions: Optional[str]
    updated_at: Optional[datetime]
    character_count: int
    
    class Config:
        from_attributes = True


class EyalStoryPromptResponse(BaseModel):
    """הפרומפט המלא לשימוש ב-AI"""
    full_prompt: str
    character_count: int


# ========== Helper Functions ==========

async def get_or_create_story(session: AsyncSession) -> EyalStory:
    """מביא או יוצר את הסיפור (תמיד שורה אחת)"""
    result = await session.execute(select(EyalStory).where(EyalStory.id == 1))
    story = result.scalar_one_or_none()
    
    if not story:
        # יצירת שורה ראשונה עם ברירת מחדל
        story = EyalStory(
            id=1,
            story_content=DEFAULT_STORY,
            forbidden_phrases=DEFAULT_FORBIDDEN,
            ai_instructions=DEFAULT_INSTRUCTIONS
        )
        session.add(story)
        await session.commit()
        await session.refresh(story)
    
    return story


# ========== Default Content ==========

DEFAULT_STORY = """🏠 ילדות והתחלות צנועות:
גדלתי ברחוב הנביאים בעיר בת ים. לא בוילה - בדירה של 2.5 חדרים.
חלקתי חדר עם אחי ואחותי עד גיל 21. אבא שלי היה שכיר, עבד קשה כל החיים.
ההורים שלי כבר לא איתנו, אבל הם לימדו אותי את הערך של עבודה קשה.
אחרי גיל 21 עברנו לבית פרטי בבית חשמונאי.
למדתי בתיכון רמות, שיחקתי כדורסל עד גיל 18.
כבר בתור נער התחלתי לעבוד - עבודה פיזית, כל מה שהיה.
עבדתי גם בקולנוע בבת ים. ידעתי שאני רוצה לבנות משהו משלי.

💪 איך למדתי הכל בעצמי:
אף אחד לא לימד אותי טכנולוגיה. למדתי הכל בעצמי דרך האינטרנט.
לא היה לי מנטור, לא היו קורסים יקרים - רק אני והמחשב.

🎖️ צבא:
שירתתי בחיל האוויר בבסיס חצור כצלם צבאי.

🚀 בגיל 20 - העסק הראשון:
בגיל 20 הקמתי את העסק הראשון שלי עם שותף.
לא היו משקיעים - מימנתי הכל בעצמי. התחלתי לעבוד מהבית.
האתגר הכי גדול: לא היה כסף לשיווק. נאלצתי להיות יצירתי.
הסיכון הכי גדול שלקחתי: לעזוב משרה בטוחה ולצאת לעצמאות.
רציתי חופש ושליטה. רציתי לבנות משהו משלי.

📹 2003 - עריכת וידאו:
הקמתי עסק לעריכת וידאו. הייתי מהחלוצים שערכו סרטי חתונה במחשב
ולא במיקסרים הישנים. הצלחתי לייצר פס ייצור של סרטי חתונה ברמה קולנועית.

🤝 2008 - הקמת Afteru Group:
פגשתי את פיני לוי, חבר מהצבא מבסיס חצור.
יחד הקמנו את Afteru Group והתחלנו בתחום ה-SEO.
בין 2008-2013 צמחנו מאפס ל-22 עובדים ו-100+ לקוחות.

📈 2013 - ההחלטה שהכפילה את הרווח:
קיבלתי החלטה אסטרטגית: לעבור מחברת שירותים לחברת מוצר.
הרווחיות קפצה מ-10%-15% ל-30%-40%! פחות כוח אדם, פחות ניהול, יותר כסף.

🏢 2016 - נדל"ן מניב:
חלמתי על הכנסה פסיבית - משהו שעובד בשבילי גם כשאני ישן.
נכנסנו לתחום הנדל"ן המניב העסקי - רכישה והשכרת משרדים.

🧮 איך התחילו המחשבונים:
רציתי להוסיף ערך לאתר שלי - משהו שגולשים ירצו להשתמש בו.
בניתי מחשבון ראשון וראיתי שזה עובד. גולשים נשארים יותר זמן, משאירים פרטים.
היום אני נותן מחשבונים בחינם - כי אני רוצה לעזור לבעלי עסקים להצליח.

💎 2017 - תכשיטים בינלאומיים:
הקמנו מיזם תכשיטים בינלאומי - מכירה לכל העולם.
ב-2022 סגרנו את המיזם והתמקדנו בטכנולוגיה.

🔄 2022 - חזרה לטכנולוגיה:
פיניתי את תפקיד המנכ"ל לשותף שלי והתמקדתי במחקר, פיתוח וטכנולוגיה.

🤖 2023 - AI:
אחרי ש-GPT הפך פופולרי, צללתי לעולם ה-AI. כמו תמיד - למדתי הכל בעצמי.
מאז 7.10 למדתי AI באופן אינטנסיבי.
היום אני בונה אפליקציות, מערכות ומאמן מודלים.
ה-AI החליף לנו כבר 4 עובדים בחברה!

👨‍👩‍👧‍👦 משפחה:
אשתי עידית - אחות דולה וגננת.
אב ל-4 ילדים - הם הכל בשבילי.
המשפחה היא התומכים הכי גדולים שלי.
בחרתי לגור בלהבים כי רציתי סביבה טובה לילדים.
אני עובד מהבית - ככה אני מאזן בין עבודה למשפחה.
אח: רן - גר בלונדון. אחות: מיכל - גרה במודיעין.

💡 הפילוסופיה שלי:
• התמדה היא הכל - נכשלתי הרבה יותר ממה שהצלחתי, אבל לא ויתרתי אף פעם
• כשיש משבר - עושים פיבוט ומסתגלים
• תמיד לאמץ טכנולוגיה חדשה
• לתת ערך לפני לבקש כסף
• אני נהנה לראות אחרים מצליחים - זה נותן לי סיפוק אמיתי

🎙️ הופעות בתקשורת:
• טיים אוט: "כשהחיים לא מחכים – המדריך השלם להלוואות"
• דבר: "התשלום האחרון שמחליט הכול"
• ביזפורטל: מומחה בתחום האשראי

🤝 תרומה לקהילה:
• תרמנו 40+ הובלות למפוני העוטף במלחמה
• 2026 היא שנת הנתינה: כל חודש 5 שעות לעזור ל-5 עסקים - בחינם

💼 תחומי המומחיות שלי:
• בניית אתרים ותכנות (למדתי הכל בעצמי!)
• שיווק דיגיטלי: Google Ads, פייסבוק, טיקטוק, SEO
• AI ואוטומציות, עריכת וידאו
• כספים, אשראי ונדל"ן מניב
"""

DEFAULT_FORBIDDEN = """עברתי ממתן שירותים למוצרי דיגיטל
עברנו משירותים למוצר
פי X יותר זמן
פי 3 יותר
פי 5 יותר
המחשבון יכפיל את הלידים שלכם
מובטח שתקבלו יותר לידים
הרווחיות שלי קפצה מ-15%"""

DEFAULT_INSTRUCTIONS = """אל תמציא מספרים או סטטיסטיקות שלא מופיעים בסיפור!
אל תשתמש במשפטים האסורים!
השתמש רק בעובדות מהסיפור - אסור להמציא!
אם אין לך מידע רלוונטי - כתוב בצורה כללית יותר.
כתוב בטון אישי וחברי - כמו שמדברים עם חבר.
המספרים המדויקים: הרווחיות עלתה מ-10%-15% ל-30%-40% (לא אחרת!)"""


# ========== Endpoints ==========

@router.get("", response_model=EyalStoryResponse)
async def get_story(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת הסיפור של אייל"""
    story = await get_or_create_story(session)
    
    return EyalStoryResponse(
        id=story.id,
        story_content=story.story_content,
        forbidden_phrases=story.forbidden_phrases,
        ai_instructions=story.ai_instructions,
        updated_at=story.updated_at,
        character_count=len(story.story_content) if story.story_content else 0
    )


@router.put("", response_model=EyalStoryResponse)
async def update_story(
    data: EyalStoryUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """עדכון הסיפור של אייל"""
    story = await get_or_create_story(session)
    
    story.story_content = data.story_content
    story.forbidden_phrases = data.forbidden_phrases
    story.ai_instructions = data.ai_instructions
    
    await session.commit()
    await session.refresh(story)
    
    return EyalStoryResponse(
        id=story.id,
        story_content=story.story_content,
        forbidden_phrases=story.forbidden_phrases,
        ai_instructions=story.ai_instructions,
        updated_at=story.updated_at,
        character_count=len(story.story_content) if story.story_content else 0
    )


@router.get("/prompt", response_model=EyalStoryPromptResponse)
async def get_full_prompt(
    session: AsyncSession = Depends(get_async_session)
):
    """קבלת הפרומפט המלא לשימוש ב-AI"""
    story = await get_or_create_story(session)
    
    full_prompt = story.get_full_prompt()
    
    return EyalStoryPromptResponse(
        full_prompt=full_prompt,
        character_count=len(full_prompt)
    )


@router.post("/test-generation")
async def test_generation(
    session: AsyncSession = Depends(get_async_session)
):
    """
    בדיקת יצירת פוסט עם הסיפור הנוכחי
    מייצר פוסט לדוגמה כדי לראות את התוצאה
    """
    from app.services.post_generator_service import get_post_generator_service
    
    story = await get_or_create_story(session)
    generator = get_post_generator_service()
    
    # יצירת פוסט לדוגמה
    result = await generator.generate_strategic_post(
        calculator_name="מחשבון פיצויים לנזקי גוף",
        calculator_url="https://example.com/calc",
        calculator_summary="מחשבון לחישוב פיצויים בתביעות נזיקין",
        strategy_system_prompt="כתוב פוסט אישי עם נתון מפתיע",
        strategy_post_template="",
        group_name="עורכי דין ישראל",
        previous_posts=[],
        include_first_comment=False
    )
    
    return {
        "generated_post": result.get("post_content"),
        "error": result.get("error"),
        "story_character_count": len(story.story_content) if story.story_content else 0,
        "forbidden_phrases_count": len(story.forbidden_phrases.split('\n')) if story.forbidden_phrases else 0
    }
