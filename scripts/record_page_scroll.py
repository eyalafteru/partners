"""
סקריפט להקלטת גלילה איטית בעמוד ושמירה כ-MP4
"""
import asyncio
import subprocess
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright לא מותקן! הרץ: pip install playwright && playwright install chromium")
    sys.exit(1)


async def record_page_scroll(
    url: str,
    output_mp4: str,
    width: int = 1920,
    height: int = 1080,
    scroll_pause: float = 0.04,
    scroll_step: int = 3,
    zoom: float = 0.85
):
    """
    מקליט גלילה איטית בעמוד ושומר כ-MP4
    
    Args:
        url: כתובת העמוד
        output_mp4: נתיב לקובץ MP4 הפלט
        width: רוחב החלון
        height: גובה החלון
        scroll_pause: השהיה בין כל צעד גלילה (שניות) - קטן יותר = חלק יותר
        scroll_step: גודל צעד גלילה בפיקסלים - קטן יותר = איטי יותר
        zoom: רמת זום (0.85 = 85%)
    """
    output_path = Path(output_mp4)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # תיקייה זמנית לקובץ webm
    temp_dir = output_path.parent / "_temp_recording"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"""
╔══════════════════════════════════════════════╗
║  🎬  מקליט גלילת עמוד                        ║
╚══════════════════════════════════════════════╝
   URL:    {url}
   פלט:    {output_mp4}
   רזולוציה: {width}x{height}
   זום:     {int(zoom*100)}%
""")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        # --- שלב 1: הכנה (סגירת עוגיות, טעינה) ---
        print("🔧 שלב 1: מכין את העמוד...")
        prep_ctx = await browser.new_context(
            viewport={"width": width, "height": height},
            locale="he-IL"
        )
        prep_page = await prep_ctx.new_page()
        await prep_page.goto(url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)
        
        # סגירת עוגיות
        for sel in ['button:has-text("אישור")', '[class*="cookie"] button', 'a:has-text("אישור")']:
            try:
                btn = await prep_page.query_selector(sel)
                if btn and await btn.is_visible():
                    await btn.click()
                    print("   🍪 עוגיות אושרו")
                    await asyncio.sleep(1)
                    break
            except:
                continue
        
        # הגדרת זום + הסתרת אלמנטים מפריעים
        await prep_page.evaluate(f"""
            document.body.style.zoom = '{zoom}';
            // הסתרת צ'אט, פופאפים וכו'
            document.querySelectorAll('[class*="chat"], [class*="popup"], [class*="modal"], [class*="sticky"], [id*="chat"]').forEach(el => el.style.display = 'none');
        """)
        await asyncio.sleep(1)
        
        # שמירת עוגיות
        cookies = await prep_ctx.cookies()
        await prep_ctx.close()
        
        # --- שלב 2: הקלטה ---
        print("🎬 שלב 2: מתחיל הקלטה...")
        rec_ctx = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(temp_dir),
            record_video_size={"width": width, "height": height},
            locale="he-IL"
        )
        await rec_ctx.add_cookies(cookies)
        page = await rec_ctx.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(1)
            
            # זום + ניקוי
            await page.evaluate(f"""
                document.body.style.zoom = '{zoom}';
                document.querySelectorAll('[class*="chat"], [class*="popup"], [class*="modal"], [class*="sticky"], [id*="chat"]').forEach(el => el.style.display = 'none');
            """)
            
            # המתנה לפני תחילת גלילה
            await asyncio.sleep(2)
            
            # גלילה איטית וחלקה
            print("📜 גולל באיטיות...")
            total_height = await page.evaluate("document.body.scrollHeight")
            viewport_height = await page.evaluate("window.innerHeight")
            current = 0
            
            while current < total_height - viewport_height:
                current += scroll_step
                await page.evaluate(f"window.scrollTo(0, {current})")
                await asyncio.sleep(scroll_pause)
                
                # הדפסת התקדמות כל 10%
                pct = int((current / (total_height - viewport_height)) * 100)
                if pct % 10 == 0 and pct > 0:
                    # בדוק אם כבר הדפסנו את האחוז הזה
                    marker = f"_pct_{pct}"
                    if not hasattr(record_page_scroll, marker):
                        setattr(record_page_scroll, marker, True)
                        print(f"   📜 {pct}%")
            
            # השהיה בסוף
            await asyncio.sleep(2)
            print("   📜 100% - הגענו לסוף העמוד!")
            
            # גלילה חזרה למעלה (חלקה)
            print("⬆️  גולל חזרה למעלה...")
            await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"⚠️ שגיאה: {e}")
        
        finally:
            # סגירה ושמירת הוידאו
            video = page.video
            await rec_ctx.close()
            await browser.close()
    
    # --- שלב 3: מציאת ה-webm והמרה ל-MP4 ---
    print("\n🔄 שלב 3: ממיר ל-MP4...")
    webm_files = sorted(temp_dir.glob("*.webm"), key=os.path.getctime, reverse=True)
    
    if not webm_files:
        print("❌ לא נמצא קובץ הקלטה!")
        return
    
    webm_file = webm_files[0]
    print(f"   קובץ מקור: {webm_file.name} ({webm_file.stat().st_size / 1024 / 1024:.1f} MB)")
    
    # המרה עם ffmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", str(webm_file),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path)
    ]
    
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=120)
    
    if result.returncode == 0 and output_path.exists():
        # ניקוי קבצים זמניים
        webm_file.unlink()
        try:
            temp_dir.rmdir()
        except:
            pass
        
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"""
╔══════════════════════════════════════════════╗
║  ✅  הוידאו נשמר בהצלחה!                     ║
╠══════════════════════════════════════════════╣
║  📁 {output_path.name}
║  📦 {size_mb:.1f} MB
║  📂 {output_path.parent}
╚══════════════════════════════════════════════╝
""")
    else:
        print(f"❌ שגיאה בהמרה: {result.stderr[-300:]}")


if __name__ == "__main__":
    URL = "https://loan-israel.co.il/category/%d7%9b%d7%9c%d7%99%d7%9d-%d7%95%d7%9e%d7%97%d7%a9%d7%91%d7%95%d7%a0%d7%99%d7%9d/"
    OUTPUT = r"D:\מחשבונים קליפ\עמוד_קטגוריית_מחשבונים.mp4"
    
    asyncio.run(record_page_scroll(
        url=URL,
        output_mp4=OUTPUT,
        width=1920,
        height=1080,
        scroll_pause=0.04,   # השהיה בין צעדים - חלק מאוד
        scroll_step=3,       # 3 פיקסלים לצעד - גלילה איטית
        zoom=0.85            # זום 85% - רואים יותר תוכן
    ))
