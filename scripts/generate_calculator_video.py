"""
PartnerCalc OS - Calculator Video Generator
כלי מקומי ליצירת סרטוני דמו למחשבונים עם Playwright

התקנה:
    pip install playwright
    playwright install chromium

שימוש:
    python generate_calculator_video.py --url "https://loan-israel.co.il/mashkanta/" --output "משכנתא.mp4"
    python generate_calculator_video.py --url "https://loan-israel.co.il/calculator/" --output "הלוואה.mp4" --duration 20
    python generate_calculator_video.py --url "..." --output "..." --captions --calc-name "מחשבון פיצויים"
"""
import asyncio
import argparse
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright לא מותקן!")
    print("להתקנה הרץ:")
    print("  pip install playwright")
    print("  playwright install chromium")
    exit(1)


class CalculatorVideoGenerator:
    """יוצר סרטוני דמו למחשבונים"""
    
    def __init__(
        self,
        url: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        duration: int = 15,
        with_captions: bool = False,
        calc_name: str = ""
    ):
        self.url = url
        self.output_path = output_path
        self.width = width
        self.height = height
        self.duration = duration  # משך הסרטון בשניות
        self.with_captions = with_captions
        self.calc_name = calc_name
        
    async def generate(self):
        """יצירת הסרטון"""
        print(f"\n🎬 מתחיל יצירת וידאו...")
        print(f"   URL: {self.url}")
        print(f"   פלט: {self.output_path}")
        print(f"   רזולוציה: {self.width}x{self.height}")
        print(f"   משך: ~{self.duration} שניות\n")
        
        async with async_playwright() as p:
            # פתיחת דפדפן ללא הקלטה - להכנה
            browser = await p.chromium.launch(headless=False)
            
            # שלב 1: הכנת העמוד (ללא הקלטה)
            print("🔧 מכין את העמוד...")
            prep_context = await browser.new_context(
                viewport={"width": self.width, "height": self.height},
                locale="he-IL"
            )
            prep_page = await prep_context.new_page()
            
            # טעינת העמוד
            print("📍 טוען את העמוד...")
            await prep_page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(2)
            
            # לחיצה על כפתור אישור עוגיות
            await self._click_cookie_consent(prep_page)
            
            # הגדרת זום
            print("🔍 מגדיר זום 60%...")
            await prep_page.evaluate("document.body.style.zoom = '0.6'")
            await asyncio.sleep(1)
            
            # סגירת ההכנה
            cookies = await prep_context.cookies()
            await prep_context.close()
            
            # שלב 2: הקלטה אמיתית
            print("🎬 מתחיל הקלטה...")
            context = await browser.new_context(
                viewport={"width": self.width, "height": self.height},
                record_video_dir=str(Path(self.output_path).parent or "."),
                record_video_size={"width": self.width, "height": self.height},
                locale="he-IL"
            )
            
            # העברת עוגיות
            await context.add_cookies(cookies)
            
            page = await context.new_page()
            
            try:
                # ניווט לעמוד
                await page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(1)
                
                # הגדרת זום מיד
                await page.evaluate("document.body.style.zoom = '0.6'")
                await asyncio.sleep(1)
                
                # === אנימציות והדגמה ===
                
                # 1. מעבר בין הטאבים של המחשבון
                await self._demo_calculator_tabs(page)
                
                # 2. משחק עם הסליידרים
                await self._demo_sliders(page)
                
                # 3. גלילה למטה לאזור ההטמעה
                await self._scroll_to_embed(page)
                
                # 4. בחירת צבע
                await self._demo_color_picker(page)
                
                # 5. העתקת קוד
                await self._demo_copy_code(page)
                
                # 6. גלילה חזרה למעלה
                print("⬆️ גולל למעלה...")
                await page.evaluate("window.scrollTo({top: 0, behavior: 'smooth'})")
                await asyncio.sleep(2)
                
                print("✅ הדגמה הושלמה!")
                
            except Exception as e:
                print(f"⚠️ שגיאה בהדגמה: {e}")
            
            finally:
                # סגירת הכל ושמירת הוידאו
                await context.close()
                await browser.close()
                
                # Playwright שומר את הוידאו אוטומטית
                # נחפש את הקובץ שנוצר ונשנה את השם
                await self._rename_video()
    
    async def _click_cookie_consent(self, page):
        """לחיצה על כפתור אישור עוגיות"""
        print("🍪 מחפש כפתור אישור עוגיות...")
        
        cookie_selectors = [
            'button:has-text("אישור")',
            'button:has-text("אשר")',
            'button:has-text("קבל")',
            'button:has-text("מסכים")',
            '[class*="cookie"] button',
            '[id*="cookie"] button',
            '.cookie-consent button',
            '#cookie-notice button',
            'a:has-text("אישור")',
            '[class*="gdpr"] button',
            '[class*="consent"] button'
        ]
        
        for selector in cookie_selectors:
            try:
                btn = await page.query_selector(selector)
                if btn:
                    is_visible = await btn.is_visible()
                    if is_visible:
                        await btn.click()
                        print("   ✓ לחצתי על אישור עוגיות")
                        await asyncio.sleep(1)
                        return
            except:
                continue
        
        print("   ℹ️ לא נמצא כפתור עוגיות")
    
    async def _demo_calculator_tabs(self, page):
        """מעבר בין טאבים של המחשבון - ספציפי למחשבונים שלנו"""
        print("🔄 עובר בין טאבים של המחשבון...")
        
        # חיפוש טאבים ספציפי למחשבונים שלנו
        tab_selectors = [
            '[data-action="switch-tab"]',  # המחשבונים שלנו
            'button[role="tab"]',
            '.tab-btn',
            '.tabs button'
        ]
        
        tabs = None
        for selector in tab_selectors:
            tabs = await page.query_selector_all(selector)
            if tabs and len(tabs) > 1:
                print(f"   ✓ נמצאו {len(tabs)} טאבים עם {selector}")
                break
        
        if tabs and len(tabs) > 1:
            for i, tab in enumerate(tabs[:4]):  # מקסימום 4 טאבים
                try:
                    # תנועת עכבר לכפתור
                    box = await tab.bounding_box()
                    if box:
                        await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        await asyncio.sleep(0.5)
                        await tab.click()
                        await asyncio.sleep(1.5)
                        
                        # קבל את שם הטאב
                        tab_name = await tab.inner_text()
                        print(f"   📑 טאב {i+1}: {tab_name.strip()[:20]}")
                except Exception as e:
                    print(f"   ⚠️ שגיאה בטאב {i+1}: {e}")
        else:
            print("   ℹ️ לא נמצאו טאבים")
            await asyncio.sleep(1)
    
    async def _demo_sliders(self, page):
        """משחק עם סליידרים - רק בטאב הנוכחי"""
        print("🎚️ מזיז סליידרים...")
        
        # חיפוש סליידרים רק בטאב הפעיל (visible)
        sliders = await page.query_selector_all('.wpc-calc-esop-x7m2-tab-content.active input[type="range"]')
        
        if not sliders or len(sliders) == 0:
            # fallback לכל הסליידרים הנראים
            sliders = await page.query_selector_all('input[type="range"]:visible')
        
        if sliders:
            print(f"   ✓ נמצאו {len(sliders)} סליידרים בטאב הפעיל")
            
            for i, slider in enumerate(sliders[:3]):  # מקסימום 3 סליידרים
                try:
                    # בדיקה אם הסליידר נראה
                    is_visible = await slider.is_visible()
                    if not is_visible:
                        continue
                    
                    box = await slider.bounding_box()
                    if box and box['width'] > 0:
                        # תנועה לסליידר
                        await page.mouse.move(box['x'] + 10, box['y'] + box['height']/2)
                        await asyncio.sleep(0.3)
                        
                        # גרירה לאמצע
                        await page.mouse.down()
                        await page.mouse.move(
                            box['x'] + box['width'] * 0.5, 
                            box['y'] + box['height']/2,
                            steps=20  # תנועה חלקה
                        )
                        await asyncio.sleep(0.5)
                        
                        # גרירה לימין
                        await page.mouse.move(
                            box['x'] + box['width'] * 0.8, 
                            box['y'] + box['height']/2,
                            steps=15
                        )
                        await page.mouse.up()
                        await asyncio.sleep(1)
                        print(f"   🎚️ סליידר {i+1}")
                except Exception as e:
                    print(f"   ⚠️ שגיאה בסליידר {i+1}")
        else:
            print("   ℹ️ לא נמצאו סליידרים נראים")
    
    async def _scroll_to_embed(self, page):
        """גלילה חלקה לאזור ההטמעה בלבד"""
        print("📜 גולל בעדינות לאזור ההטמעה...")
        
        # חיפוש אזור ההטמעה וגלילה אליו
        embed_selectors = [
            '#wpc-calc-esop-x7m2-embed',
            '[class*="embed-section"]',
            '#color-picker'
        ]
        
        for selector in embed_selectors:
            embed = await page.query_selector(selector)
            if embed:
                # קבלת המיקום של אזור ההטמעה
                box = await embed.bounding_box()
                if box:
                    # גלילה חלקה למיקום - עם מרווח מלמעלה
                    target_scroll = box['y'] - 100  # מרווח של 100px מלמעלה
                    
                    # גלילה הדרגתית
                    current_scroll = await page.evaluate("window.scrollY")
                    steps = 3
                    for i in range(1, steps + 1):
                        intermediate = current_scroll + (target_scroll - current_scroll) * (i / steps)
                        await page.evaluate(f"window.scrollTo({{top: {intermediate}, behavior: 'smooth'}})")
                        await asyncio.sleep(0.8)
                    
                    print(f"   ✓ הגענו לאזור ההטמעה")
                    return
        
        # fallback - גלילה קצרה
        await page.evaluate("""
            window.scrollTo({
                top: document.body.scrollHeight * 0.4,
                behavior: 'smooth'
            })
        """)
        await asyncio.sleep(1.5)
        print(f"   ✓ גלילה הושלמה")
    
    async def _demo_color_picker(self, page):
        """הדגמת בחירת צבע"""
        print("🎨 מדגים בחירת צבע...")
        
        # חיפוש כפתורי צבע ספציפי למחשבונים שלנו
        color_selectors = [
            '[data-action="preview-color"]',  # המחשבונים שלנו
            '.color-picker button',
            '.color-btn',
            '[class*="color-btn"]'
        ]
        
        color_buttons = None
        for selector in color_selectors:
            color_buttons = await page.query_selector_all(selector)
            if color_buttons and len(color_buttons) > 1:
                print(f"   ✓ נמצאו {len(color_buttons)} צבעים")
                break
        
        if color_buttons and len(color_buttons) > 1:
            # לחיצה על 3 צבעים שונים
            colors_to_try = [1, 3, 5]  # אינדקסים של צבעים מעניינים
            
            for idx in colors_to_try:
                if idx < len(color_buttons):
                    try:
                        btn = color_buttons[idx]
                        await btn.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        
                        box = await btn.bounding_box()
                        if box:
                            # תנועת עכבר
                            await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                            await asyncio.sleep(0.5)
                            
                            # לחיצה
                            await btn.click()
                            await asyncio.sleep(1.5)
                            
                            # קבל את שם הצבע
                            color_name = await btn.get_attribute('data-name') or await btn.get_attribute('title') or f'צבע {idx+1}'
                            print(f"   🎨 {color_name}")
                    except Exception as e:
                        print(f"   ⚠️ שגיאה בצבע {idx}: {e}")
        else:
            print("   ℹ️ לא נמצא Color Picker")
    
    async def _demo_copy_code(self, page):
        """הדגמת העתקת קוד"""
        print("📋 מדגים העתקת קוד...")
        
        # חיפוש כפתור העתקה
        copy_selectors = [
            '[data-action="copy-embed-code"]',  # המחשבונים שלנו
            '[data-action="copy-preview-code"]',
            'button:has-text("העתק")',
            '[class*="embed-btn"]'
        ]
        
        for selector in copy_selectors:
            try:
                copy_btn = await page.query_selector(selector)
                if copy_btn:
                    await copy_btn.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    
                    box = await copy_btn.bounding_box()
                    if box:
                        # תנועת עכבר לכפתור
                        await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        await asyncio.sleep(0.8)
                        
                        # הדגשה ויזואלית (hover)
                        await asyncio.sleep(0.5)
                        
                        # לחיצה
                        await copy_btn.click()
                        await asyncio.sleep(1)
                        
                        print(f"   ✓ כפתור העתקה נלחץ")
                        
                        # סגירת alert אם יש
                        try:
                            page.on("dialog", lambda dialog: dialog.accept())
                        except:
                            pass
                        
                        return
            except Exception as e:
                continue
        
        print("   ℹ️ לא נמצא כפתור העתקה")
    
    async def _rename_video(self):
        """שינוי שם קובץ הוידאו שנוצר"""
        # Playwright יוצר קובץ עם שם אקראי
        video_dir = Path(self.output_path).parent or Path(".")
        
        # חיפוש הקובץ האחרון שנוצר
        webm_files = list(video_dir.glob("*.webm"))
        if webm_files:
            latest = max(webm_files, key=os.path.getctime)
            target = Path(self.output_path)
            
            # אם הפלט הוא mp4, נצטרך להמיר (דורש ffmpeg)
            if target.suffix.lower() == '.mp4':
                print(f"\n⚠️ Playwright יוצר קבצי WebM.")
                print(f"   הקובץ נשמר כ: {latest}")
                print(f"\n   להמרה ל-MP4 הרץ:")
                print(f"   ffmpeg -i \"{latest}\" \"{target}\"")
            else:
                # מחיקת קובץ קיים אם יש
                if target.exists():
                    target.unlink()
                # שינוי שם
                latest.rename(target)
                print(f"\n✅ הוידאו נשמר: {target}")
                
                # הוספת כתוביות אם נדרש
                if self.with_captions:
                    await self._add_captions(target)
    
    async def _add_captions(self, video_path: Path):
        """הוספת כתוביות פתיחה וסיום לוידאו עם FFmpeg"""
        print("\n🎬 מוסיף כתוביות לוידאו...")
        
        # בדיקה אם FFmpeg מותקן
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            # נסה נתיב ספציפי של Windows
            win_ffmpeg = r"C:\Users\eyal\AppData\Local\Microsoft\WinGet\Links\ffmpeg.exe"
            if os.path.exists(win_ffmpeg):
                ffmpeg_path = win_ffmpeg
            else:
                print("   ⚠️ FFmpeg לא נמצא - דילוג על כתוביות")
                return
        
        # חיפוש פונט עברית
        font_paths = [
            r"C:/Windows/Fonts/arial.ttf",
            r"C:/Windows/Fonts/tahoma.ttf",
            r"C:/Windows/Fonts/segoeui.ttf",
        ]
        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp.replace("\\", "/").replace(":", "\\\\:")
                break
        
        if not font_path:
            print("   ⚠️ לא נמצא פונט מתאים - דילוג על כתוביות")
            return
        
        # טקסטים לכתוביות
        calc_name = self.calc_name or "מחשבון"
        intro_line1 = calc_name
        intro_line2 = "להטמעה בקליק באתרך"
        outro_text = "לחצו והטמיעו באתרכם בקליק!"
        
        # קבלת משך הוידאו
        probe_cmd = [
            ffmpeg_path, "-i", str(video_path), 
            "-f", "null", "-"
        ]
        try:
            result = subprocess.run(
                probe_cmd, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            # חיפוש Duration בפלט
            import re
            duration_match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
            if duration_match:
                h, m, s = duration_match.groups()
                total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
            else:
                total_seconds = 30  # ברירת מחדל
        except:
            total_seconds = 30
        
        # חישוב זמני הכתוביות
        intro_start = 0
        intro_end = 3  # 3 שניות פתיחה
        outro_start = max(0, total_seconds - 4)  # 4 שניות לפני הסוף
        outro_end = total_seconds
        
        # יצירת פילטר FFmpeg לכתוביות
        # כתובית פתיחה - שם המחשבון (גדול) + טקסט משנה (קטן יותר)
        # כתובית סיום
        drawtext_filter = (
            # רקע כהה לפתיחה
            f"drawbox=x=0:y=ih/2-80:w=iw:h=160:color=black@0.7:t=fill:enable='between(t,{intro_start},{intro_end})',"
            # שורה 1 - שם המחשבון
            f"drawtext=fontfile='{font_path}':text='{intro_line1}':fontsize=48:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h-text_h)/2-30:enable='between(t,{intro_start},{intro_end})',"
            # שורה 2 - טקסט משנה
            f"drawtext=fontfile='{font_path}':text='{intro_line2}':fontsize=32:fontcolor=yellow:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+30:enable='between(t,{intro_start},{intro_end})',"
            # רקע כהה לסיום
            f"drawbox=x=0:y=ih/2-50:w=iw:h=100:color=black@0.7:t=fill:enable='between(t,{outro_start},{outro_end})',"
            # כתובית סיום
            f"drawtext=fontfile='{font_path}':text='{outro_text}':fontsize=36:fontcolor=lime:"
            f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{outro_start},{outro_end})'"
        )
        
        # קובץ פלט זמני
        output_with_captions = video_path.with_stem(video_path.stem + "_captioned")
        
        # הרצת FFmpeg
        ffmpeg_cmd = [
            ffmpeg_path,
            "-i", str(video_path),
            "-vf", drawtext_filter,
            "-c:a", "copy",
            "-y",  # overwrite
            str(output_with_captions)
        ]
        
        print(f"   🔄 מעבד וידאו עם FFmpeg...")
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0 and output_with_captions.exists():
                # החלפת הקובץ המקורי
                video_path.unlink()
                output_with_captions.rename(video_path)
                print(f"   ✅ כתוביות נוספו בהצלחה!")
            else:
                print(f"   ⚠️ שגיאה בהוספת כתוביות: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print("   ⚠️ FFmpeg timeout - דילוג על כתוביות")
        except Exception as e:
            print(f"   ⚠️ שגיאה: {e}")


async def main():
    parser = argparse.ArgumentParser(
        description="יצירת סרטון דמו למחשבון עם Playwright"
    )
    parser.add_argument(
        "--url", "-u",
        required=True,
        help="URL של עמוד המחשבון"
    )
    parser.add_argument(
        "--output", "-o",
        default=f"calculator_demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm",
        help="שם קובץ הפלט (ברירת מחדל: calculator_demo_TIMESTAMP.webm)"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=1280,
        help="רוחב הוידאו (ברירת מחדל: 1280)"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=720,
        help="גובה הוידאו (ברירת מחדל: 720)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=int,
        default=15,
        help="משך הדגמה בשניות (ברירת מחדל: 15)"
    )
    parser.add_argument(
        "--captions", "-c",
        action="store_true",
        help="הוסף כתוביות פתיחה וסיום לוידאו"
    )
    parser.add_argument(
        "--calc-name", "-n",
        type=str,
        default="",
        help="שם המחשבון לכתובית הפתיחה"
    )
    
    args = parser.parse_args()
    
    generator = CalculatorVideoGenerator(
        url=args.url,
        output_path=args.output,
        width=args.width,
        height=args.height,
        duration=args.duration,
        with_captions=args.captions,
        calc_name=args.calc_name
    )
    
    await generator.generate()


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║     🎬 PartnerCalc OS - Calculator Video Generator        ║
║        יוצר סרטוני דמו למחשבונים עם Playwright             ║
╚═══════════════════════════════════════════════════════════╝
    """)
    asyncio.run(main())
