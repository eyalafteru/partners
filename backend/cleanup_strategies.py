"""
סקריפט לניקוי האסטרטגיות מהסיפור המוטמע
ושימוש בשורטקודים במקום
"""
import asyncio
import re
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.post_strategy import PostStrategy

# דפוסים לזיהוי סיפור מוטמע שצריך להסיר
STORY_PATTERNS = [
    r'📖 סיפורים אמיתיים מהחיים של אייל.*?(?=✍️ הוראות כתיבה:|⚠️ אזהרות:|$)',
    r'🏠 סיפור הילדות:.*?(?=✍️|⚠️|$)',
    r'🎬 סיפור העסק הראשון:.*?(?=📹|🤝|📈|🧮|💡|✍️|⚠️|$)',
    r'📹 סיפור עריכת הווידאו:.*?(?=🤝|📈|🧮|💡|✍️|⚠️|$)',
    r'🤝 סיפור השותפות:.*?(?=📈|🧮|💡|✍️|⚠️|$)',
    r'📈 סיפור המעבר למוצר:.*?(?=🧮|💡|✍️|⚠️|$)',
    r'🧮 סיפור המחשבונים:.*?(?=💡|✍️|⚠️|$)',
    r'💡 סיפור ה-AI:.*?(?=✍️|⚠️|$)',
    r'"גדלתי ברחוב הנביאים.*?"',
    r'"בגיל 20 הקמתי.*?"',
    r'"ב-2003 הייתי מהחלוצים.*?"',
    r'"פגשתי את פיני לוי.*?"',
    r'"ב-2013 קיבלתי החלטה.*?"',
    r'"רציתי להוסיף ערך לאתר.*?"',
    r'"אחרי ש-GPT הפך פופולרי.*?"',
    r'גדלתי ברחוב הנביאים בבת ים\. דירה של 2\.5 חדרים.*?עובד בשבילו\."',
    r'הרווחיות קפצה מ-10%-15% ל-30%-40%!',
]

# טקסט להוספה במקום הסיפור
SHORTCODE_NOTE = """
📌 הערה חשובה:
הסיפור המלא של אייל, המשפטים האסורים וההוראות - מוזרקים אוטומטית מהדאטאבייס.
אין צורך לכלול אותם כאן. התמקד רק בהנחיות הספציפיות לאסטרטגיה הזו.
"""


def clean_strategy_prompt(prompt: str, strategy_name: str) -> str:
    """מנקה את הפרומפט מהסיפור המוטמע"""
    if not prompt:
        return prompt
    
    original_length = len(prompt)
    cleaned = prompt
    
    # הסרת בלוקים של סיפורים
    # מחפש את הבלוק של "סיפורים אמיתיים" ומסיר אותו
    story_block_pattern = r'📖 סיפורים אמיתיים מהחיים של אייל שאפשר להשתמש בהם:.*?(?=✍️ הוראות כתיבה:|$)'
    cleaned = re.sub(story_block_pattern, '', cleaned, flags=re.DOTALL)
    
    # הסרת סיפורים בודדים
    individual_stories = [
        r'🏠 סיפור הילדות:\s*"[^"]+"\s*',
        r'🎬 סיפור העסק הראשון:\s*"[^"]+"\s*',
        r'📹 סיפור עריכת הווידאו:\s*"[^"]+"\s*',
        r'🤝 סיפור השותפות:\s*"[^"]+"\s*',
        r'📈 סיפור המעבר למוצר:\s*"[^"]+"\s*',
        r'🧮 סיפור המחשבונים:\s*"[^"]+"\s*',
        r'💡 סיפור ה-AI:\s*"[^"]+"\s*',
    ]
    
    for pattern in individual_stories:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    
    # הסרת ציטוטים ספציפיים מהסיפור
    specific_quotes = [
        r'"גדלתי ברחוב הנביאים[^"]*"',
        r'"בגיל 20 הקמתי[^"]*"',
        r'"ב-2003 הייתי מהחלוצים[^"]*"',
        r'"פגשתי את פיני לוי[^"]*"',
        r'"ב-2013 קיבלתי החלטה[^"]*"',
        r'"רציתי להוסיף ערך[^"]*"',
        r'"אחרי ש-GPT הפך[^"]*"',
        r'"התחלתי לעבוד מהבית[^"]*"',
        r'"לא היו משקיעים[^"]*"',
        r'"הצלחתי לייצר פס ייצור[^"]*"',
        r'"מ-2008 עד 2013 צמחנו[^"]*"',
        r'"הרווחיות קפצה[^"]*"',
        r'"היום אני נותן מחשבונים[^"]*"',
        r'"היום ה-AI החליף[^"]*"',
    ]
    
    for pattern in specific_quotes:
        cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL)
    
    # הסרת שורות ריקות מרובות
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # הסרת רווחים מיותרים
    cleaned = cleaned.strip()
    
    new_length = len(cleaned)
    if new_length < original_length:
        print(f"  ✅ Cleaned {original_length - new_length} chars from {strategy_name}")
    
    return cleaned


async def main():
    print("=" * 60)
    print("🧹 מנקה אסטרטגיות מסיפור מוטמע")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # שליפת כל האסטרטגיות
        result = await session.execute(select(PostStrategy))
        strategies = result.scalars().all()
        
        print(f"\n📋 נמצאו {len(strategies)} אסטרטגיות\n")
        
        updated_count = 0
        
        for strategy in strategies:
            print(f"\n{'─' * 40}")
            print(f"📝 {strategy.name} ({strategy.slug})")
            
            original_prompt = strategy.system_prompt or ""
            
            # בדיקה אם יש סיפור מוטמע
            has_story = any([
                'גדלתי ברחוב הנביאים' in original_prompt,
                'בגיל 20 הקמתי' in original_prompt,
                'ב-2003 הייתי מהחלוצים' in original_prompt,
                'פגשתי את פיני לוי' in original_prompt,
                'ב-2013 קיבלתי החלטה' in original_prompt,
                'סיפורים אמיתיים מהחיים של אייל' in original_prompt,
                'הרווחיות קפצה מ-10%-15%' in original_prompt,
            ])
            
            if has_story:
                print(f"  ⚠️ מכיל סיפור מוטמע - מנקה...")
                cleaned_prompt = clean_strategy_prompt(original_prompt, strategy.name)
                
                # עדכון בדאטאבייס
                strategy.system_prompt = cleaned_prompt
                updated_count += 1
                
                print(f"  📊 לפני: {len(original_prompt)} תווים")
                print(f"  📊 אחרי: {len(cleaned_prompt)} תווים")
            else:
                print(f"  ✓ נקי - אין סיפור מוטמע")
        
        # שמירה
        if updated_count > 0:
            await session.commit()
            print(f"\n{'=' * 60}")
            print(f"✅ עודכנו {updated_count} אסטרטגיות בהצלחה!")
            print("=" * 60)
        else:
            print(f"\n{'=' * 60}")
            print("ℹ️ לא נמצאו אסטרטגיות לעדכון")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
