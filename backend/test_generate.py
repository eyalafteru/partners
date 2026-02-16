"""בדיקה של יצירת פוסט עם דיבאג"""
import asyncio
from app.services.post_generator_service import get_post_generator_service

async def test_generate():
    generator = get_post_generator_service()
    
    # יצירת פוסט
    result = await generator.generate_strategic_post(
        calculator_name="מחשבון פיצויים לתביעות נזיקין",
        calculator_url="https://loan-israel.co.il/pitzuim/",
        calculator_summary="מחשבון לחישוב פיצויים בתביעות נזיקין",
        strategy_system_prompt="""╔══════════════════════════════════════════════════════════════════════════════╗
║                     אסטרטגיה: נתון מפתיע 📊                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

🎯 מהות האסטרטגיה:
נתון מפתיע תופס תשומת לב. אנשים אוהבים ללמוד משהו חדש.

📌 הערה חשובה:
הנתונים והעובדות האמיתיות נמצאים בסיפור של אייל שמוזרק אוטומטית.
השתמש רק בנתונים משם - אסור להמציא!

✍️ הוראות כתיבה:
1. פתח עם נתון או עובדה מהסיפור של אייל שתפתיע
2. הסבר למה זה רלוונטי
3. חבר את הנתון למחשבון
4. סיים עם: "רוצים להטמיע מחשבון כזה? תגיבו ואשלח קוד"
5. טון: משכנע אבל לא דוחף
6. אורך: 4-6 שורות

⚠️ אזהרות:
• אל תמציא מספרים שלא מופיעים בסיפור של אייל!
• אל תכלול קישורים בפוסט""",
        strategy_post_template="",
        group_name="עורכי דין - נזיקין ותביעות",
        previous_posts=[],
        include_first_comment=False
    )
    
    print("=" * 80)
    print("GENERATED POST:")
    print("=" * 80)
    print(result.get("post_content"))
    print()
    print("=" * 80)
    print("DEBUG - SYSTEM MESSAGE (first 2000 chars):")
    print("=" * 80)
    print((result.get("debug_system_message") or "")[:2000])
    print()
    print("=" * 80)
    print("DEBUG - USER PROMPT (first 3000 chars):")
    print("=" * 80)
    print((result.get("debug_full_prompt") or "")[:3000])

if __name__ == "__main__":
    asyncio.run(test_generate())
