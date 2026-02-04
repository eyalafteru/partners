"""
PartnerCalc OS - Seed Strategies Script
סקריפט לטעינת 10 אסטרטגיות מובנות
"""
import asyncio
from sqlalchemy import select
from loguru import logger

from app.database import AsyncSessionLocal
from app.models.post_strategy import PostStrategy


# 10 אסטרטגיות מובנות
STRATEGIES = [
    {
        "name": "שיפור SEO",
        "slug": "seo",
        "icon": "📈",
        "description": "פוסט שמדגיש יתרונות SEO",
        "system_prompt": """אתה כותב פוסט שמדגיש את היתרונות של הטמעת מחשבון לשיפור SEO.
הדגש: תוכן אינטראקטיבי, זמן שהייה ארוך יותר, bounce rate נמוך, 
Google אוהב עמודים עם כלים שימושיים.""",
        "post_template": """רוצים לשפר את ה-SEO של האתר שלכם? 📈

גילוי מפתיע: Google מעדיף אתרים עם תוכן אינטראקטיבי!

פיתחתי מחשבון {calculator_name} שאפשר להטמיע בחינם באתר שלכם.
הגולשים נשארים יותר זמן, ה-bounce rate יורד, והאתר עולה בדירוגים.

לינק: {calculator_url}""",
        "sort_order": 1
    },
    {
        "name": "יצירת לידים",
        "slug": "lead_gen",
        "icon": "🎯",
        "description": "פוסט שמדגיש יצירת לידים חמים",
        "system_prompt": """אתה כותב פוסט שמדגיש איך המחשבון עוזר ליצור לידים חמים.
הדגש: לידים איכותיים, אנשים שמשתמשים במחשבון מתעניינים באמת,
קל להמיר אותם ללקוחות.""",
        "post_template": """איך לייצר לידים חמים בלי לשלם על מודעות? 🎯

התשובה: לתת ערך אמיתי קודם!

המחשבון {calculator_name} שפיתחתי עוזר לאנשים לקבל תשובות -
ומי שמשתמש בו כבר מתעניין בנושא.

הטמעה בחינם: {calculator_url}""",
        "sort_order": 2
    },
    {
        "name": "מיתוג אישי",
        "slug": "white_label",
        "icon": "🏷️",
        "description": "פוסט שמדגיש התאמה אישית",
        "system_prompt": """אתה כותב פוסט שמדגיש את האפשרות להתאמה אישית של המחשבון.
הדגש: שינוי צבעים, התאמה לעיצוב האתר, נראה כאילו אתם פיתחתם אותו.""",
        "post_template": """רוצים מחשבון באתר שנראה כאילו אתם פיתחתם אותו? 🏷️

המחשבון {calculator_name} שלי מאפשר:
✅ שינוי צבעים בלחיצה
✅ התאמה לעיצוב האתר
✅ בלי לוגו שלי - רק שלכם

הטמעה חינמית: {calculator_url}""",
        "sort_order": 3
    },
    {
        "name": "חווית משתמש",
        "slug": "ux",
        "icon": "✨",
        "description": "פוסט שמדגיש UX מעולה",
        "system_prompt": """אתה כותב פוסט שמדגיש את חווית המשתמש המעולה של המחשבון.
הדגש: פשוט לשימוש, תוצאות מיידיות, עיצוב מודרני, ידידותי למשתמש.""",
        "post_template": """חווית משתמש מעולה = לקוחות מרוצים ✨

המחשבון {calculator_name} תוכנן עם UX מוקפד:
• פשוט - מילוי תוך שניות
• מיידי - תוצאות ללא המתנה
• יפה - עיצוב מודרני ונקי

נסו בעצמכם: {calculator_url}""",
        "sort_order": 4
    },
    {
        "name": "תאימות מובייל",
        "slug": "mobile_first",
        "icon": "📱",
        "description": "פוסט שמדגיש תאימות מובייל",
        "system_prompt": """אתה כותב פוסט שמדגיש את התאימות המלאה למובייל.
הדגש: 70% מהגלישה ממובייל, responsive design, עובד מושלם בכל מכשיר.""",
        "post_template": """70% מהגולשים שלכם במובייל - האתר מוכן? 📱

המחשבון {calculator_name} מותאם לחלוטין:
• עובד מושלם בכל גודל מסך
• Touch-friendly
• טעינה מהירה

בדקו עכשיו מהנייד: {calculator_url}""",
        "sort_order": 5
    },
    {
        "name": "בניית סמכות",
        "slug": "authority",
        "icon": "👑",
        "description": "פוסט שמדגיש בניית אמינות",
        "system_prompt": """אתה כותב פוסט שמדגיש איך המחשבון בונה סמכות ואמינות.
הדגש: מקצועיות, אתר עם כלים = אתר רציני, מומחיות בתחום.""",
        "post_template": """רוצים שהלקוחות יראו בכם מומחים? 👑

אתר עם כלים מקצועיים = אתר שסומכים עליו.

המחשבון {calculator_name} שפיתחתי ישדרג את האמינות שלכם מיידית.
הטמעה בחינם תוך דקות.

כאן: {calculator_url}""",
        "sort_order": 6
    },
    {
        "name": "אפס תחזוקה",
        "slug": "zero_maintenance",
        "icon": "🔧",
        "description": "פוסט שמדגיש חוסר תחזוקה",
        "system_prompt": """אתה כותב פוסט שמדגיש שאין צורך בתחזוקה.
הדגש: Embed פשוט, אני מעדכן, אתם לא צריכים לעשות כלום.""",
        "post_template": """מחשבון באתר בלי כאב ראש של תחזוקה? 🔧

זה בדיוק מה שאני מציע:
• הטמעה פעם אחת בקופי-פייסט
• אני מעדכן - אתם נהנים
• עובד 24/7 בלי התערבות

{calculator_name}: {calculator_url}""",
        "sort_order": 7
    },
    {
        "name": "יתרון תחרותי",
        "slug": "competitive_edge",
        "icon": "🏆",
        "description": "פוסט שמדגיש יתרון על מתחרים",
        "system_prompt": """אתה כותב פוסט שמדגיש את היתרון על המתחרים.
הדגש: הם לא מציעים את זה, תהיו שונים, ערך מוסף ייחודי.""",
        "post_template": """מה יש לכם שאין למתחרים? 🏆

רוב האתרים בתחום עדיין בלי כלים אינטראקטיביים.

הוסיפו את המחשבון {calculator_name} והפכו את האתר לייחודי.
הגולשים יזכרו אתכם.

הטמעה חינמית: {calculator_url}""",
        "sort_order": 8
    },
    {
        "name": "ויראליות",
        "slug": "social_shares",
        "icon": "🔄",
        "description": "פוסט שמדגיש פוטנציאל ויראלי",
        "system_prompt": """אתה כותב פוסט שמדגיש את הפוטנציאל הויראלי.
הדגש: אנשים משתפים כלים שימושיים, תוכן ויראלי, חשיפה אורגנית.""",
        "post_template": """תוכן שאנשים באמת משתפים? 🔄

כלים שימושיים מקבלים שיתופים אורגניים!

המחשבון {calculator_name} שווה שיתוף - 
ואנשים באמת משתפים אותו עם חברים.

הוסיפו לאתר: {calculator_url}""",
        "sort_order": 9
    },
    {
        "name": "הטמעה קלה",
        "slug": "developer_friendly",
        "icon": "💻",
        "description": "פוסט שמדגיש פשטות טכנית",
        "system_prompt": """אתה כותב פוסט שמדגיש את הפשטות הטכנית.
הדגש: קוד פשוט, קופי-פייסט, לא צריך מתכנת, עובד בכל פלטפורמה.""",
        "post_template": """הטמעה בלי לשלם למתכנת? 💻

המחשבון {calculator_name} מוכן להטמעה ב-3 צעדים:
1️⃣ העתק את הקוד
2️⃣ הדבק באתר
3️⃣ זה הכל!

עובד ב-WordPress, Wix, כל דבר.
קוד להעתקה: {calculator_url}""",
        "sort_order": 10
    },
]


async def seed_strategies():
    """טעינת אסטרטגיות לבסיס הנתונים"""
    async with AsyncSessionLocal() as session:
        added = 0
        updated = 0
        
        for strategy_data in STRATEGIES:
            # בדיקה אם קיים
            result = await session.execute(
                select(PostStrategy).where(PostStrategy.slug == strategy_data["slug"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # עדכון קיים
                for key, value in strategy_data.items():
                    setattr(existing, key, value)
                updated += 1
                logger.info(f"🔄 Updated strategy: {strategy_data['name']}")
            else:
                # יצירת חדש
                strategy = PostStrategy(**strategy_data)
                session.add(strategy)
                added += 1
                logger.info(f"✅ Added strategy: {strategy_data['name']}")
        
        await session.commit()
        
        logger.info(f"📊 Seed complete: {added} added, {updated} updated")
        return {"added": added, "updated": updated}


if __name__ == "__main__":
    asyncio.run(seed_strategies())
