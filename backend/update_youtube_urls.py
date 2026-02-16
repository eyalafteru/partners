"""
עדכון כתובות YouTube למחשבונים
"""
import asyncio
from sqlalchemy import select, update
from app.database import AsyncSessionLocal
from app.models.calculator import Calculator

# מיפוי ID מחשבון -> YouTube URL
YOUTUBE_URLS = {
    1: "https://youtu.be/-ZVA1KnchAU",   # מחשבון שווי אופציות
    2: "https://youtu.be/_qnPGZ4KO6g",   # מחשבון פיצויים לתביעות נזיקין
    3: "https://youtu.be/CfGCCLMKpx0",   # מחשבון עצמאי מול שכיר
    4: "https://youtu.be/3j25DXI9Uz0",   # מחשבון עלות מעסיק
    5: "https://youtu.be/zhYht-s_ylQ",   # מחשבון ברוטו נטו
    6: "https://youtu.be/4NMQPmSH7-Y",   # מחשבון ריבית אפקטיבית
    7: "https://youtu.be/2cGSclGiSd8",   # מחשבון קיצור זמן הלוואה
    8: "https://youtu.be/b9JPTcnqfis",   # מחשבון עמלת פירעון מוקדם
    9: "https://youtu.be/T9LJXpUji0Y",   # מחשבון הלוואת בלון
    10: "https://youtu.be/2syiuLfUq60",  # מחשבון ניכיון צ'קים
    11: "https://youtu.be/Wi4K9DxvD6s",  # מחשבון איחוד הלוואות
    12: "https://youtu.be/m0rEu3zTnXc",  # מחשבון ריבית דריבית
    13: "https://youtu.be/gCZBbPy4SPU",  # מחשבון הלוואות
    14: "https://youtu.be/ZiHPH3y8DR8",  # מחשבון עלות רכב אמיתית
    15: "https://youtu.be/yYduLV1Hwf8",  # מחשבון יחס החזר
    16: "https://youtu.be/0LWadZDYJ2E",  # מחשבון שווי שימוש ברכב
    17: "https://youtu.be/BGFYgph_xac",  # מחשבון מס רכישה
    18: "https://youtu.be/M2amr2AwSkk",  # מחשבון מדד תשומות בנייה
    19: "https://youtu.be/AzCIRSg7Rzc",  # מחשבון שכירות מול רכישה
    20: "https://youtu.be/5JYPM9JwQEA",  # מחשבון משכנתא
    21: "https://youtu.be/nV6xf1fJAOw",  # מחשבון חופש כלכלי
    22: "https://youtu.be/5YGdoGSQY1s",  # מחשבון פנסיה
    23: "https://youtu.be/3RDu83uwyzg",  # מחשבון חיסכון מתקדם
}

async def update_youtube_urls():
    async with AsyncSessionLocal() as session:
        for calc_id, youtube_url in YOUTUBE_URLS.items():
            result = await session.execute(
                update(Calculator)
                .where(Calculator.id == calc_id)
                .values(youtube_url=youtube_url)
            )
            print(f"✅ Updated calculator {calc_id} with {youtube_url}")
        
        await session.commit()
        print("\n🎉 All YouTube URLs updated!")

if __name__ == "__main__":
    asyncio.run(update_youtube_urls())
