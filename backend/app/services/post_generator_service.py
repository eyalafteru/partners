"""
PartnerCalc OS - Post Generator Service
שירות ליצירת פוסטים ו-prompts לתמונות עם GPT
"""
import httpx
import random
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings
from app.services.replicate_service import get_replicate_service


# ========== מיפוי מחשבונים לקהלי יעד ==========
CALCULATOR_TARGET_AUDIENCES = {
    # מחשבונים משפטיים
    "פיצויים": "עורכי דין, משרדי עורכי דין, חברות לזכויות רפואיות, יועצי נזיקין",
    "נזיקין": "עורכי דין, משרדי עורכי דין, חברות לזכויות רפואיות, יועצי נזיקין",
    "תביעות": "עורכי דין, משרדי עורכי דין, חברות לזכויות רפואיות",
    
    # מחשבונים פיננסיים
    "הלוואות": "יועצים פיננסיים, סוכני ביטוח, ברוקרים, אתרי השוואת הלוואות",
    "הלוואה": "יועצים פיננסיים, סוכני ביטוח, ברוקרים, אתרי השוואת הלוואות",
    "משכנתא": "יועצי משכנתאות, סוכני נדל\"ן, אתרי נדל\"ן, בנקים",
    "אשראי": "יועצים פיננסיים, חברות אשראי, סוכני ביטוח",
    "ריבית": "יועצים פיננסיים, רואי חשבון, בנקים, אתרי השקעות",
    "חיסכון": "יועצי השקעות, סוכני ביטוח, בתי השקעות, בנקים",
    "פנסיה": "סוכני ביטוח, יועצי פנסיה, חברות ביטוח, רואי חשבון",
    
    # מחשבונים לשכירים ועצמאיים
    "שכר": "חברות כוח אדם, מנהלי HR, רואי חשבון, יועצי מס",
    "נטו": "חברות כוח אדם, מנהלי HR, רואי חשבון, יועצי מס",
    "ברוטו": "חברות כוח אדם, מנהלי HR, רואי חשבון, יועצי מס",
    "עצמאי": "רואי חשבון, יועצי מס, יועצים עסקיים, פורטלים לעצמאיים",
    "מעסיק": "חברות כוח אדם, מנהלי HR, רואי חשבון, יועצי עסקים",
    
    # מחשבוני רכב ונדל"ן
    "רכב": "סוכני רכב, אתרי רכב, חברות ליסינג, סוכני ביטוח רכב",
    "ליסינג": "סוכני רכב, חברות ליסינג, יועצים פיננסיים",
    "נדל\"ן": "סוכני נדל\"ן, יזמי נדל\"ן, אתרי נדל\"ן, יועצי משכנתאות",
    "שכירות": "סוכני נדל\"ן, אתרי השכרה, יזמי נדל\"ן",
    
    # ברירת מחדל
    "default": "בעלי אתרים, יועצים פיננסיים, סוכני ביטוח, רואי חשבון"
}

def get_target_audience_for_calculator(calculator_name: str) -> str:
    """מחזיר את קהל היעד המתאים למחשבון לפי שם המחשבון"""
    calculator_lower = calculator_name.lower() if calculator_name else ""
    
    for keyword, audience in CALCULATOR_TARGET_AUDIENCES.items():
        if keyword != "default" and keyword in calculator_lower:
            return audience
    
    return CALCULATOR_TARGET_AUDIENCES["default"]


# ========== פונקציה למשיכת הסיפור מהדאטאבייס ==========
async def get_eyal_story_from_db() -> str:
    """
    מביא את הסיפור של אייל מהדאטאבייס כולל משפטים אסורים והוראות
    אם אין - מחזיר את ברירת המחדל
    """
    try:
        from app.database import AsyncSessionLocal
        from app.models.eyal_story import EyalStory
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(EyalStory).where(EyalStory.id == 1))
            story = result.scalar_one_or_none()
            
            if story:
                full_prompt = story.get_full_prompt()
                logger.info(f"✅ Eyal story fetched from DB: {len(story.story_content or '')} chars story, "
                           f"{len(story.forbidden_phrases or '')} chars forbidden, "
                           f"{len(story.ai_instructions or '')} chars instructions")
                return full_prompt
            else:
                logger.warning("⚠️ Eyal story not found in DB (id=1), using fallback")
                return EYAL_STORY_FALLBACK
    except Exception as e:
        logger.error(f"❌ Failed to fetch Eyal story from DB: {e}", exc_info=True)
        return EYAL_STORY_FALLBACK


# ========== סיפור ברירת מחדל (fallback) ==========
EYAL_STORY_FALLBACK = """
הסיפור של אייל עובדיה:
גדלתי ברחוב הנביאים בבת ים, בדירה של 2.5 חדרים.
בגיל 20 הקמתי את העסק הראשון שלי. למדתי הכל בעצמי.
ב-2008 הקמתי את Afteru Group עם פיני לוי, צמחנו ל-22 עובדים.
ב-2013 עברתי מחברת שירותים לחברת מוצר - הרווחיות קפצה מ-10%-15% ל-30%-40%.
היום אני נותן מחשבונים בחינם לבעלי אתרים.
אב ל-4 ילדים, גר בלהבים, עובד מהבית.

אזהרה: אסור להמציא עובדות! השתמש רק במה שכתוב כאן.
"""


# ========== הסיפור המלא של אייל עובדיה - עובדות מאומתות בלבד! ==========
# זה הסיפור האישי שלי - כל מה שכתוב כאן הוא אמת ומאומת
# ה-AI חייב להשתמש רק בעובדות מתוך הסיפור הזה ולא להמציא שום דבר!

EYAL_STORY = """
══════════════════════════════════════════════════════════════════
                    הסיפור המלא של אייל עובדיה
           השתמש רק בעובדות מכאן - אסור להמציא שום דבר!
══════════════════════════════════════════════════════════════════

🏠 ילדות והתחלות צנועות:
───────────────────────────────────────
גדלתי ברחוב הנביאים בעיר בת ים. לא בוילה - בדירה של 2.5 חדרים. 
חלקתי חדר עם אחי ואחותי עד גיל 21. אבא שלי היה שכיר, עבד קשה כל החיים.
ההורים שלי כבר לא איתנו, אבל הם לימדו אותי את הערך של עבודה קשה.

אחרי גיל 21 עברנו לבית פרטי בבית חשמונאי - זה היה שדרוג משמעותי.
למדתי בתיכון רמות, שיחקתי כדורסל עד גיל 18.
כבר בתור נער התחלתי לעבוד - עבודה פיזית, כל מה שהיה. 
עבדתי גם בקולנוע בבת ים. ידעתי שאני רוצה לבנות משהו משלי.

💪 איך למדתי הכל בעצמי:
───────────────────────────────────────
אף אחד לא לימד אותי טכנולוגיה. למדתי הכל בעצמי דרך האינטרנט.
לא היה לי מנטור, לא היו קורסים יקרים - רק אני והמחשב.
זה לימד אותי שאפשר ללמוד כל דבר לבד אם רק רוצים מספיק חזק.

🎖️ צבא:
───────────────────────────────────────
שירתתי בחיל האוויר בבסיס חצור כצלם צבאי.
שם למדתי צילום ועריכה - זה מה שהוביל אותי אחר כך לעסק הראשון.

🚀 בגיל 20 - העסק הראשון:
───────────────────────────────────────
בגיל 20 הקמתי את העסק הראשון שלי עם שותף.
לא היו משקיעים - מימנתי הכל בעצמי. התחלתי לעבוד מהבית.
האתגר הכי גדול: לא היה כסף לשיווק. נאלצתי להיות יצירתי.
הסיכון הכי גדול שלקחתי: לעזוב משרה בטוחה ולצאת לעצמאות.
רציתי חופש ושליטה. רציתי לבנות משהו משלי.

📹 2003 - עריכת וידאו:
───────────────────────────────────────
הקמתי עסק לעריכת וידאו. הייתי מהחלוצים שערכו סרטי חתונה במחשב 
ולא במיקסרים הישנים. הצלחתי לייצר פס ייצור של סרטי חתונה ברמה קולנועית.
המוצר הראשון שלי היה תבנית אתר - הבנתי שמוצרים עובדים טוב יותר משירותים.

🤝 2008 - הקמת Afteru Group:
───────────────────────────────────────
פגשתי את פיני לוי, חבר מהצבא מבסיס חצור. 
יחד הקמנו את Afteru Group והתחלנו בתחום ה-SEO.
בין 2008-2013 צמחנו ל-22 עובדים ו-100+ לקוחות.
היינו אחת מסוכנויות הקידום המובילות בישראל.

📈 2013 - ההחלטה שהכפילה את הרווח:
───────────────────────────────────────
קיבלתי החלטה אסטרטגית: לעבור מחברת שירותים לחברת מוצר.
הרווחיות קפצה מ-10%-15% ל-30%-40%! פחות כוח אדם, פחות ניהול.
זה לימד אותי: מוצרים עדיפים על שירותים.

🏢 2016 - נדל"ן מניב:
───────────────────────────────────────
חלמתי על הכנסה פסיבית - משהו שעובד בשבילי גם כשאני ישן.
נכנסנו לתחום הנדל"ן המניב העסקי - רכישה והשכרת משרדים.
פיזור הכנסות חכם.

🧮 איך התחילו המחשבונים:
───────────────────────────────────────
רציתי להוסיף ערך לאתר שלי - משהו שגולשים ירצו להשתמש בו.
בניתי מחשבון ראשון וראיתי שזה עובד. גולשים נשארים יותר זמן, משאירים פרטים.
היום אני נותן מחשבונים בחינם - כי אני רוצה לעזור לבעלי עסקים להצליח.
לא רק בשביל הלידים - כי אני נהנה לראות אחרים מצליחים.

💎 2017 - תכשיטים בינלאומיים:
───────────────────────────────────────
הקמנו מיזם תכשיטים בינלאומי - מכירה לכל העולם.
ב-2022 סגרנו את המיזם והתמקדנו בטכנולוגיה - ידעתי לעשות פיבוט כשצריך.

🔄 2022 - חזרה לטכנולוגיה:
───────────────────────────────────────
פיניתי את תפקיד המנכ"ל לשותף שלי והתמקדתי במחקר, פיתוח וטכנולוגיה.
תמיד הייתי מוכן לאמץ טכנולוגיה חדשה - זה מה ששינה את העסק שלי.

🤖 2023 - AI:
───────────────────────────────────────
אחרי ש-GPT הפך פופולרי, צללתי לעולם ה-AI. כמו תמיד - למדתי הכל בעצמי.
מאז 7.10 למדתי AI באופן אינטנסיבי.
היום אני בונה אפליקציות, מערכות ומאמן מודלים.
ה-AI החליף לנו כבר 4 עובדים בחברה!

👨‍👩‍👧‍👦 משפחה - הכל:
───────────────────────────────────────
אשתי עידית - אחות דולה וגננת. 
אב ל-4 ילדים - הם הכל בשבילי.
המשפחה היא התומכים הכי גדולים שלי.
בחרתי לגור בלהבים כי רציתי סביבה טובה לילדים.
אני עובד מהבית - ככה אני מאזן בין עבודה למשפחה.
אוהב בשר טוב, טיולים בארץ ובעולם, זמן איכות עם המשפחה.

אח: רן - גר בלונדון. אחות: מיכל - גרה במודיעין.

💡 הפילוסופיה שלי:
───────────────────────────────────────
• התמדה היא הכל - נכשלתי הרבה יותר ממה שהצלחתי, אבל לא ויתרתי אף פעם
• כשיש משבר - עושים פיבוט ומסתגלים
• תמיד לאמץ טכנולוגיה חדשה
• לתת ערך לפני לבקש כסף
• אני נהנה לראות אחרים מצליחים - זה נותן לי סיפוק אמיתי

🎙️ הופעות בתקשורת:
───────────────────────────────────────
• טיים אוט: "כשהחיים לא מחכים – המדריך השלם להלוואות"
• דבר: "התשלום האחרון שמחליט הכול"
• ביזפורטל: מומחה בתחום האשראי
• חיפה פה, סלונה

🤝 תרומה לקהילה:
───────────────────────────────────────
• תרמנו 40+ הובלות למפוני העוטף במלחמה
• 2026 היא שנת הנתינה: כל חודש 5 שעות לעזור ל-5 עסקים - בחינם
• הערכים שאני רוצה להעביר לילדים: עבודה קשה והתמדה

🎯 סגנון התקשורת שלי:
───────────────────────────────────────
• חברי וחם - מדבר עם אנשים כמו חברים
• ישיר ואותנטי - בלי שטויות
• עוזר בלי לצפות לתמורה

💼 תחומי המומחיות שלי:
───────────────────────────────────────
• בניית אתרים ותכנות (למדתי הכל בעצמי!)
• שיווק דיגיטלי: Google Ads, פייסבוק, טיקטוק, SEO
• AI ואוטומציות, עריכת וידאו
• כספים, אשראי ונדל"ן מניב
• איפיון מוצרים ומעבר משירות למוצר
• ייעול תהליכי עבודה ואוטומציה

══════════════════════════════════════════════════════════════════
                    ⚠️ אזהרה חמורה ל-AI ⚠️
══════════════════════════════════════════════════════════════════
1. אסור להמציא עובדות על אייל! רק מה שכתוב למעלה!
2. אם אין מידע רלוונטי - כתוב בצורה כללית יותר
3. אל תמציא מספרים, תאריכים או שמות שלא מופיעים כאן
4. הפוסט צריך להרגיש אמיתי כי הוא מבוסס על סיפור אמיתי
══════════════════════════════════════════════════════════════════
"""

# Alias for backward compatibility
EYAL_PROFILE = EYAL_STORY

# Prompt ליצירת וריאציה של פוסט - פוסט אישי מאייל עובדיה
POST_VARIATION_PROMPT = """אתה כותב פוסט אישי עבור אייל עובדיה לפייסבוק.

{eyal_profile}

🎯 מטרת הפוסט: לגרום לבעלי אתרים להטמיע את המחשבון באתר שלהם (בחינם!)

שם הקבוצה: {group_name}
קהל יעד: {target_audience}
תבנית בסיס (אם יש): {base_template}

📝 דרישות לפוסט:
1. כתוב בגוף ראשון - "אני", "שלי", "פיתחתי"
2. טון אישי, ידידותי, לא מכירתי
3. אורך: 4-7 שורות
4. הדגש שזה בחינם ומתוך רצון לעזור לבעלי אתרים
5. הזכר את הניסיון שלי או את הרקע שלי בצורה טבעית
6. קריאה לפעולה: "תגיבו ואשלח לכם את הקישור" / "מי רוצה שאשלח לינק?"
7. השתמש ב-2-3 אימוג'ים רלוונטיים (לא יותר מדי)
8. התאם לסוג הקבוצה (עסקים, שיווק, אתרים, נדל"ן, AI וכו')
9. כל פוסט צריך להיות שונה ויצירתי - לא לחזור על אותן פתיחות וסגנונות

⚠️ חשוב מאוד:
- אל תכלול קישורים בפוסט עצמו! הקישור יישלח בתגובה נפרדת
- המטרה היא להטמיע את המחשבון באתר של הקורא, לא שהקורא ישתמש במחשבון

פוסטים קודמים (להימנע מחזרות):
{previous_posts}

הנחיות נוספות:
{additional_instructions}

החזר רק את טקסט הפוסט, ללא הסברים וללא קישורים."""

# Prompt ליצירת prompt לתמונה - דינמי וויראלי
VIRAL_IMAGE_PROMPT_EYAL = """Create a VIRAL, eye-catching image prompt for FLUX AI model featuring "eyal".

Facebook Post (in Hebrew):
{post_content}

Previous prompt to AVOID (create something DIFFERENT):
{previous_prompt}

Create a unique, scroll-stopping image about WEBSITE CALCULATOR EMBEDDING!

Requirements:
1. MUST START WITH: "A photo of eyal,"
2. eyal is a professional Israeli businessman in his 40s
3. Make it VIRAL - dramatic angles, interesting compositions
4. Theme: Helping website owners embed calculators on their sites
5. Ideas vary: eyal pointing at computer screen showing embedded calculator, eyal explaining code to someone, eyal next to website mockup with calculator widget, eyal holding laptop showing calculator on website, eyal in tech environment with code visible
6. Include visual elements: computer screens, code snippets (blurred), website mockups, calculator interfaces
7. Vary the settings: modern office, tech hub, co-working space, standing at whiteboard
8. Emotions: helpful, approachable, sharing knowledge, giving
9. NO text, words, or logos
10. End with: "4k quality, viral social media photo, professional tech"

Be CREATIVE and DIFFERENT from the previous prompt! Format: 50-80 words.

Return ONLY the image prompt."""

VIRAL_IMAGE_PROMPT_GENERIC = """Create a VIRAL, eye-catching image prompt for FLUX AI model.

Facebook Post (in Hebrew):
{post_content}

Previous prompt to AVOID (create something DIFFERENT):
{previous_prompt}

Create a unique, scroll-stopping image about EMBEDDING CALCULATORS ON WEBSITES!

Requirements:
1. NO people's faces - use abstract concepts, objects, or silhouettes
2. Make it VIRAL - dramatic, colorful, eye-catching
3. Theme: Embedding financial calculators/widgets on websites - free tools for website owners
4. Ideas: laptop showing website with embedded calculator widget, code snippets flowing into website mockup, website wireframe with calculator component highlighted, multiple screens showing different calculator widgets, modern dashboard with embed code visible, puzzle piece (calculator) fitting into website
5. Style: Modern, sleek, tech-forward, helpful
6. Colors: Bold blues, greens, gold accents, gradients
7. Lighting: Dramatic, futuristic, or bright optimistic
8. NO text, words, or logos
9. End with: "4k quality, viral social media graphic, professional tech"

Be CREATIVE and DIFFERENT from the previous prompt! Format: 50-80 words.

Return ONLY the image prompt."""


class PostGeneratorService:
    """שירות יצירת פוסטים עם GPT/Claude"""
    
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.anthropic_api_key = getattr(settings, 'anthropic_api_key', '')
        self.default_model = getattr(settings, 'default_ai_model', 'gpt-4o-mini')
        self.replicate_service = get_replicate_service()
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.openai_api_key) or bool(self.anthropic_api_key)
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """רשימת מודלים זמינים"""
        models = []
        if self.openai_api_key:
            models.extend([
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini (מהיר וזול)"},
                {"id": "gpt-4o", "name": "GPT-4o (איכותי)"},
            ])
        if self.anthropic_api_key:
            models.extend([
                {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"},
                {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5 (הכי חדש)"},
            ])
        return models
    
    async def _call_ai(
        self,
        prompt: str,
        system_message: str = "You are a helpful marketing assistant.",
        model: str = None,
        temperature: float = 0.8,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        קריאה ל-AI (GPT או Claude)
        """
        if not self.is_configured:
            logger.error("No AI API key configured")
            return None
        
        # בחירת מודל ברירת מחדל
        if model is None:
            model = self.default_model
        
        # Claude models
        if model.startswith("claude"):
            return await self._call_claude(prompt, system_message, model, temperature, max_tokens)
        # OpenAI models
        else:
            return await self._call_openai(prompt, system_message, model, temperature, max_tokens)
    
    async def _call_openai(
        self,
        prompt: str,
        system_message: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """קריאה ל-OpenAI GPT"""
        if not self.openai_api_key:
            logger.error("OpenAI API key not configured")
            return None
        
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"OpenAI call error: {e}")
            return None
    
    async def _call_claude(
        self,
        prompt: str,
        system_message: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """קריאה ל-Anthropic Claude"""
        if not self.anthropic_api_key:
            logger.error("Anthropic API key not configured")
            return None
        
        # Map friendly names to API model names
        model_map = {
            "claude-sonnet-4": "claude-sonnet-4-20250514",
            "claude-sonnet-4-5": "claude-sonnet-4-5-20250514",
        }
        api_model = model_map.get(model, model)
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": api_model,
            "max_tokens": max_tokens,
            "system": system_message,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"].strip()
                else:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Claude call error: {e}")
            return None
    
    # Backward compatibility
    async def _call_gpt(self, *args, **kwargs) -> Optional[str]:
        return await self._call_ai(*args, **kwargs)
    
    async def generate_post_variation(
        self,
        topic: str,
        group_name: str,
        target_audience: str = "",
        base_template: str = "",
        previous_posts: List[str] = None,
        additional_instructions: str = "",
        model: str = None
    ) -> Optional[str]:
        """
        יצירת וריאציה ייחודית של פוסט
        
        Args:
            topic: נושא הפוסט
            group_name: שם הקבוצה
            target_audience: קהל היעד
            base_template: תבנית בסיס (אופציונלי)
            previous_posts: פוסטים קודמים להימנע מחזרות
            additional_instructions: הנחיות נוספות
            
        Returns:
            טקסט הפוסט, או None בשגיאה
        """
        # הכנת רשימת פוסטים קודמים
        prev_posts_text = "אין"
        if previous_posts and len(previous_posts) > 0:
            # מציג את 3 האחרונים
            recent = previous_posts[-3:]
            prev_posts_text = "\n".join([f"- {p[:100]}..." for p in recent])
        
        # שליפת הסיפור של אייל מהדאטאבייס
        eyal_story = await get_eyal_story_from_db()
        
        prompt = POST_VARIATION_PROMPT.format(
            eyal_profile=eyal_story,
            topic=topic,
            group_name=group_name,
            target_audience=target_audience or "כללי",
            base_template=base_template or "אין - צור מאפס",
            previous_posts=prev_posts_text,
            additional_instructions=additional_instructions or "אין"
        )
        
        # בחירת מודל זמין אם לא סופק
        if model is None:
            model = self._get_available_model()
        
        result = await self._call_ai(
            prompt=prompt,
            system_message="אתה כותב פוסטים אישיים עבור אייל עובדיה - יזם, מייסד Afteru Group וחוקר AI עם 20+ שנות ניסיון. הפוסטים נכתבים בגוף ראשון, בטון אישי וידידותי, ומציעים מחשבונים פיננסיים להטמעה בחינם. אתה כותב בעברית.",
            model=model,
            temperature=0.85
        )
        
        if result:
            logger.info(f"📝 ✅ Post generated for group: {group_name}")
        
        return result
    
    async def generate_image_prompt(
        self,
        post_content: str,
        topic: str = "",
        model: str = None
    ) -> Optional[str]:
        """
        יצירת prompt לתמונה על בסיס הפוסט
        
        Args:
            post_content: תוכן הפוסט (עברית)
            topic: נושא הפוסט
            model: מודל AI לשימוש (אופציונלי)
            
        Returns:
            prompt לתמונה (אנגלית), או None בשגיאה
        """
        prompt = IMAGE_PROMPT_GENERATOR.format(
            post_content=post_content,
            topic=topic or "general marketing"
        )
        
        # בחירת מודל זמין
        if model is None:
            model = self._get_available_model()
        
        result = await self._call_ai(
            prompt=prompt,
            system_message="You are an expert at creating image prompts for AI image generators.",
            model=model,
            temperature=0.7
        )
        
        if result:
            logger.info(f"🎨 ✅ Image prompt generated")
        
        return result
    
    def _get_available_model(self) -> str:
        """מחזיר מודל זמין - Claude מועדף על GPT"""
        # Claude מועדף - איכות כתיבה בעברית טובה יותר
        if self.anthropic_api_key:
            return "claude-sonnet-4"
        elif self.openai_api_key:
            return "gpt-4o-mini"
        return self.default_model
    
    async def generate_viral_image_prompt(
        self,
        post_content: str,
        style: str = "eyal",
        previous_prompt: str = None,
        model: str = None
    ) -> Optional[str]:
        """
        יצירת prompt וירלי ודינמי לתמונה
        
        Args:
            post_content: תוכן הפוסט (עברית)
            style: "eyal" לתמונה עם אייל, "generic" לתמונה גנרית
            previous_prompt: פרומפט קודם להימנע ממנו
            model: מודל AI לשימוש
            
        Returns:
            prompt לתמונה (אנגלית), או None בשגיאה
        """
        # בחירת טמפלט לפי סגנון
        if style == "eyal":
            template = VIRAL_IMAGE_PROMPT_EYAL
        else:
            template = VIRAL_IMAGE_PROMPT_GENERIC
        
        prompt = template.format(
            post_content=post_content,
            previous_prompt=previous_prompt or "None - this is the first image"
        )
        
        # בחירת מודל זמין
        if model is None:
            model = self._get_available_model()
        
        result = await self._call_ai(
            prompt=prompt,
            system_message="You are a viral social media image expert. Create unique, scroll-stopping image prompts that get engagement. Be creative and vary your outputs!",
            model=model,
            temperature=0.95  # Higher temperature for more creativity
        )
        
        if result:
            logger.info(f"🎨 ✅ Viral image prompt generated ({style})")
        
        return result
    
    async def generate_full_post(
        self,
        topic: str,
        group_name: str,
        include_image: bool = True,
        target_audience: str = "",
        base_template: str = "",
        previous_posts: List[str] = None,
        additional_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        יצירת פוסט מלא עם/בלי תמונה
        
        Args:
            topic: נושא הפוסט
            group_name: שם הקבוצה
            include_image: האם לכלול תמונה
            target_audience: קהל היעד
            base_template: תבנית בסיס
            previous_posts: פוסטים קודמים
            additional_instructions: הנחיות נוספות
            
        Returns:
            dict עם content, image_url, image_prompt
        """
        result = {
            "content": None,
            "has_image": False,
            "image_prompt": None,
            "image_url": None,
            "error": None
        }
        
        # שלב 1: יצירת טקסט הפוסט
        post_content = await self.generate_post_variation(
            topic=topic,
            group_name=group_name,
            target_audience=target_audience,
            base_template=base_template,
            previous_posts=previous_posts,
            additional_instructions=additional_instructions
        )
        
        if not post_content:
            result["error"] = "Failed to generate post content"
            return result
        
        result["content"] = post_content
        
        # שלב 2: יצירת תמונה (אם נדרש)
        if include_image:
            # יצירת prompt לתמונה
            image_prompt = await self.generate_image_prompt(
                post_content=post_content,
                topic=topic
            )
            
            if image_prompt:
                result["image_prompt"] = image_prompt
                
                # יצירת התמונה עצמה
                image_url = await self.replicate_service.generate_post_image(
                    image_prompt=image_prompt
                )
                
                if image_url:
                    result["has_image"] = True
                    result["image_url"] = image_url
                    logger.info(f"📸 ✅ Full post with image generated for: {group_name}")
                else:
                    logger.warning(f"📸 ⚠️ Image generation failed, post will be without image")
            else:
                logger.warning(f"🎨 ⚠️ Image prompt generation failed")
        else:
            logger.info(f"📝 ✅ Post generated (no image) for: {group_name}")
        
        return result
    
    async def generate_campaign_posts(
        self,
        topic: str,
        groups: List[Dict[str, Any]],
        image_percentage: int = 50,
        base_template: str = "",
        target_audience: str = ""
    ) -> List[Dict[str, Any]]:
        """
        יצירת פוסטים לכל הקבוצות בקמפיין
        
        Args:
            topic: נושא הקמפיין
            groups: רשימת קבוצות (dict עם id, name)
            image_percentage: אחוז פוסטים עם תמונה
            base_template: תבנית בסיס
            target_audience: קהל יעד
            
        Returns:
            רשימת פוסטים שנוצרו
        """
        posts = []
        previous_posts = []
        
        for i, group in enumerate(groups):
            # החלטה אם לכלול תמונה
            include_image = random.randint(1, 100) <= image_percentage
            
            logger.info(f"📝 Generating post {i+1}/{len(groups)} for {group.get('name')}...")
            
            post = await self.generate_full_post(
                topic=topic,
                group_name=group.get("name", ""),
                include_image=include_image,
                target_audience=target_audience,
                base_template=base_template,
                previous_posts=previous_posts
            )
            
            post["group_id"] = group.get("id")
            post["group_name"] = group.get("name")
            posts.append(post)
            
            # שמירת הפוסט לרשימת הקודמים
            if post.get("content"):
                previous_posts.append(post["content"])
        
        logger.info(f"📦 Generated {len(posts)} posts for campaign")
        return posts
    
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: str = None
    ) -> Optional[str]:
        """
        יצירת טקסט פשוט עם AI
        
        Args:
            prompt: ההנחיה
            max_tokens: מספר מקסימלי של טוקנים
            temperature: טמפרטורה
            model: מודל לשימוש
            
        Returns:
            הטקסט שנוצר
        """
        if model is None:
            model = self._get_available_model()
        
        return await self._call_ai(
            prompt=prompt,
            system_message="You are a helpful assistant.",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_strategic_post(
        self,
        calculator_name: str,
        calculator_url: str,
        calculator_summary: str,
        strategy_system_prompt: str,
        strategy_post_template: str,
        group_name: str,
        previous_posts: List[str] = None,
        include_first_comment: bool = False,
        model: str = None
    ) -> Dict[str, Any]:
        """
        יצירת פוסט עם אסטרטגיה ומחשבון ספציפי
        
        Args:
            calculator_name: שם המחשבון
            calculator_url: קישור למחשבון
            calculator_summary: תקציר AI של המחשבון
            strategy_system_prompt: הנחיות האסטרטגיה ל-AI (תומך במשתנים: {group_name}, {calculator_name}, {calculator_url}, {calculator_summary})
            strategy_post_template: תבנית הפוסט (תומך במשתנים: {group_name}, {calculator_name}, {calculator_url}, {calculator_summary})
            group_name: שם הקבוצה
            previous_posts: פוסטים קודמים
            include_first_comment: האם ליצור תגובה ראשונה עם הקישור
            model: מודל AI לשימוש
            
        Returns:
            dict עם post_content, first_comment_content
        """
        result = {
            "post_content": None,
            "first_comment_content": None,
            "error": None,
            "debug_full_prompt": None,  # 🐞 DEBUG: הפרומפט המלא שנשלח ל-AI
            "debug_system_message": None  # 🐞 DEBUG: ה-system message שנשלח
        }
        
        # === החלפת משתנים דינמיים ב-prompts ===
        # משתנים זמינים: {group_name}, {calculator_name}, {calculator_url}, {calculator_summary}
        replacements = {
            "{group_name}": group_name or "",
            "{calculator_name}": calculator_name or "",
            "{calculator_url}": calculator_url or "",
            "{calculator_summary}": calculator_summary or ""
        }
        
        # החלפה ב-system prompt
        formatted_system_prompt = strategy_system_prompt or ""
        for key, value in replacements.items():
            formatted_system_prompt = formatted_system_prompt.replace(key, value)
        
        # החלפה ב-post template
        formatted_post_template = strategy_post_template or ""
        for key, value in replacements.items():
            formatted_post_template = formatted_post_template.replace(key, value)
        
        logger.debug(f"🔄 Replaced dynamic variables for group: {group_name}, calculator: {calculator_name}")
        
        # תמיד צור עם AI - לכל קבוצה פוסט ייחודי!
        # (strategy_post_template משמש כהנחיות נוספות, לא כתבנית קבועה)
        
        # שליפת הסיפור של אייל מהדאטאבייס (כולל משפטים אסורים והוראות)
        eyal_story = await get_eyal_story_from_db()
        logger.debug(f"📖 Fetched Eyal story from DB ({len(eyal_story)} chars)")
        
        # קביעת קהל יעד לפי סוג המחשבון
        target_audience_for_calc = get_target_audience_for_calculator(calculator_name)
        logger.debug(f"🎯 Target audience for '{calculator_name}': {target_audience_for_calc}")
        
        # בניית prompt ממוקד עם מאגר עובדות
        prompt = f"""
{eyal_story}

═══════════════════════════════════════════════════════════
📝 צור פוסט לקבוצת פייסבוק "{group_name}"
═══════════════════════════════════════════════════════════

🧮 המחשבון: {calculator_name}
תיאור: {calculator_summary or 'מחשבון פיננסי חכם להטמעה בחינם באתרים'}

👥 קהל יעד: {target_audience_for_calc}

📌 אסטרטגיה: {formatted_system_prompt or 'כתוב פוסט אישי ומושך'}
{f'סגנון: {formatted_post_template}' if formatted_post_template else ''}

📋 פוסטים קודמים (חובה להשתמש בעובדות אחרות!):
{chr(10).join(['- ' + p[:100] + '...' for p in (previous_posts[-5:] if previous_posts else [])]) or 'אין'}

═══════════════════════════════════════════════════════════
📐 מבנה חובה - 3 עד 5 שורות בלבד:
═══════════════════════════════════════════════════════════

שורה 1: HOOK - פתיחה שעוצרת גלילה (שאלה / עובדה / תובנה מפתיעה)
שורה 2-3: VALUE - הערך של המחשבון לבעלי אתרים (הם מציעים אותו ללקוחות שלהם, לא משתמשים בו בעצמם)
שורה 4-5: CTA - "תגיבו 'רוצה' ואשלח לכם לינק" / "רוצים? תגיבו ואשלח"

═══════════════════════════════════════════════════════════
✅ דוגמאות לפוסטים מצוינים (כל אחד משתמש בעובדות שונות):
═══════════════════════════════════════════════════════════

דוגמה 1 (עובדה: למדתי הכל בעצמי + מחשבונים):
"אף אחד לא לימד אותי טכנולוגיה. למדתי הכל לבד מול המחשב 💪
אחרי 20+ שנה בדיגיטל, בניתי מחשבון {calculator_name} שאפשר להטמיע בכל אתר - בחינם.
בעלי אתרים שמטמיעים את זה מקבלים גולשים שנשארים יותר זמן ומשאירים פרטים.
רוצים? תגיבו ואשלח לכם לינק 🎁"

דוגמה 2 (עובדה: Afteru Group + שנת הנתינה):
"ב-2008 הקמתי את Afteru Group, היום אחרי 100+ לקוחות אני יודע דבר אחד:
אתר בלי כלים אינטראקטיביים מפסיד גולשים 🎯
בניתי מחשבון {calculator_name} שבעלי אתרים יכולים להטמיע בחינם - בלחיצת כפתור.
2026 זו שנת הנתינה שלי - תגיבו 'רוצה' ואשלח!"

דוגמה 3 (עובדה: עבודה מהבית + AI):
"עובד מהבית, אב ל-4 ילדים, ובונה מחשבונים בעזרת AI 🤖
בניתי {calculator_name} שאפשר להטמיע בכל אתר - וורדפרס, וויקס, מה שלא יהיה.
ההטמעה חינמית ולוקחת דקה. מי רוצה שאשלח לינק?"

═══════════════════════════════════════════════════════════

⚠️ כללים:
- 3-5 שורות בלבד! לא יותר!
- אסור קישורים בפוסט
- בחר 1-2 עובדות מקטגוריות שונות מהסיפור - כל פוסט עובדות אחרות!
- גוף ראשון, טון ידידותי, 1-2 אימוג'ים
- המטרה: בעלי אתרים יטמיעו את המחשבון באתר שלהם

החזר רק את טקסט הפוסט, ללא הסברים.
"""
        
        if model is None:
            model = self._get_available_model()
        
        # System message - קצר וממוקד
        system_message = f"""אתה כותב פוסטים קצרים וממוקדים בעברית עבור אייל עובדיה.
גוף ראשון, טון אישי וידידותי - כמו הודעה לחבר.

כללים קשיחים:
- 3-5 שורות בלבד
- אסור קישורים בפוסט (הקישור בתגובה נפרדת)
- סיום עם CTA: "תגיבו 'רוצה' ואשלח לינק" או וריאציה דומה
- בחר 1-2 עובדות מקטגוריות שונות מהסיפור - כל פוסט עובדות אחרות!
- 1-2 אימוג'ים, לא יותר
- אסור להמציא עובדות, מספרים או סטטיסטיקות!

המטרה: בעלי אתרים ({target_audience_for_calc}) יטמיעו מחשבון חינמי באתר שלהם בלחיצת כפתור.
הם מציעים אותו ללקוחות שלהם - לא משתמשים בו בעצמם."""
        
        # 🐞 DEBUG: שמירת הפרומפט לתוצאה
        result["debug_full_prompt"] = prompt
        result["debug_system_message"] = system_message
        
        # 🐞 DEBUG: לוג מפורט
        logger.info(f"🐞 === DEBUG: FULL PROMPT SENT TO AI ===")
        logger.info(f"🐞 Model: {model}")
        logger.info(f"🐞 System message length: {len(system_message)} chars")
        logger.info(f"🐞 Full prompt length: {len(prompt)} chars")
        logger.info(f"🐞 Eyal story in prompt: {'YES' if 'הסיפור של אייל' in prompt or 'אייל עובדיה' in prompt else 'NO'}")
        
        post_content = await self._call_ai(
            prompt=prompt,
            system_message=system_message,
            model=model,
            temperature=0.7  # Balanced: creative but focused
        )
        
        if not post_content:
            result["error"] = "Failed to generate post content"
            return result
        
        result["post_content"] = post_content
        
        # יצירת תגובה ראשונה (אם נדרש)
        if include_first_comment:
            first_comment = f"""🔗 הנה הקישור למחשבון:
{calculator_url}

מחשבון {calculator_name} - הטמעה חינמית באתר שלכם!
לשאלות - שלחו הודעה 💬"""
            result["first_comment_content"] = first_comment
        
        logger.info(f"📝 ✅ Strategic post generated for {group_name} with calculator {calculator_name}")
        return result


# Singleton
_post_generator: Optional[PostGeneratorService] = None


def get_post_generator_service() -> PostGeneratorService:
    """קבלת instance של Post Generator Service"""
    global _post_generator
    if _post_generator is None:
        _post_generator = PostGeneratorService()
    return _post_generator
