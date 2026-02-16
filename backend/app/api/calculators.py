"""
PartnerCalc OS - Calculators API
CRUD פעולות למחשבונים
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_async_session
from app.models.calculator import Calculator

router = APIRouter()


# ========== Pydantic Schemas ==========

class CalculatorCreate(BaseModel):
    """סכמה ליצירת מחשבון"""
    name: str
    target_url: str
    intent_description: Optional[str] = None
    keywords: Optional[List[str]] = None
    embed_code_template: Optional[str] = None
    category: Optional[str] = "הלוואות ומימון"
    is_active: bool = True


class CalculatorUpdate(BaseModel):
    """סכמה לעדכון מחשבון"""
    name: Optional[str] = None
    target_url: Optional[str] = None
    intent_description: Optional[str] = None
    keywords: Optional[List[str]] = None
    embed_code_template: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    demo_video_url: Optional[str] = None


class CalculatorResponse(BaseModel):
    """סכמה לתגובה"""
    id: int
    name: str
    target_url: str
    intent_description: Optional[str]
    keywords: Optional[List[str]]
    embed_code_template: Optional[str]
    category: Optional[str]
    is_active: bool
    # AI fields
    ai_summary: Optional[str] = None
    scraped_content: Optional[str] = None
    scraped_at: Optional[datetime] = None
    # Video demo
    demo_video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class VideoUpdateRequest(BaseModel):
    """סכמה לעדכון וידאו"""
    demo_video_url: str


class YouTubeUploadRequest(BaseModel):
    """סכמה להעלאה ליוטיוב"""
    title: Optional[str] = None  # אם לא סופק, ישתמש בשם המחשבון
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    privacy: str = "unlisted"  # public, unlisted, private


# ========== API Endpoints ==========

@router.get("/", response_model=List[CalculatorResponse])
async def list_calculators(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת רשימת כל המחשבונים
    """
    query = select(Calculator)
    
    if active_only:
        query = query.where(Calculator.is_active == True)
    
    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    
    return result.scalars().all()


@router.get("/count")
async def count_calculators(
    session: AsyncSession = Depends(get_async_session)
):
    """
    ספירת מחשבונים
    """
    result = await session.execute(select(func.count(Calculator.id)))
    total = result.scalar()
    
    result = await session.execute(
        select(func.count(Calculator.id)).where(Calculator.is_active == True)
    )
    active = result.scalar()
    
    return {"total": total, "active": active}


@router.get("/{calc_id}", response_model=CalculatorResponse)
async def get_calculator(
    calc_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת מחשבון לפי ID
    """
    from loguru import logger
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    # Force refresh from DB to get latest data
    await session.refresh(calculator)
    
    logger.info(f"GET Calculator {calc_id}: youtube_url={calculator.youtube_url}, demo_video_url={calculator.demo_video_url}")
    
    return calculator


@router.post("/", response_model=CalculatorResponse)
async def create_calculator(
    data: CalculatorCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    יצירת מחשבון חדש
    """
    calculator = Calculator(
        name=data.name,
        target_url=data.target_url,
        intent_description=data.intent_description,
        keywords=data.keywords,
        embed_code_template=data.embed_code_template,
        category=data.category,
        is_active=data.is_active
    )
    
    session.add(calculator)
    await session.flush()
    await session.refresh(calculator)
    
    return calculator


@router.put("/{calc_id}", response_model=CalculatorResponse)
async def update_calculator(
    calc_id: int,
    data: CalculatorUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון מחשבון קיים
    """
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    # עדכון שדות
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(calculator, field, value)
    
    await session.flush()
    await session.refresh(calculator)
    
    return calculator


@router.delete("/{calc_id}")
async def delete_calculator(
    calc_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת מחשבון
    """
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    await session.delete(calculator)
    
    return {"message": f"מחשבון {calc_id} נמחק בהצלחה"}


# ========== Video Demo Endpoints ==========

@router.put("/{calc_id}/video", response_model=CalculatorResponse)
async def update_calculator_video(
    calc_id: int,
    data: VideoUpdateRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    עדכון URL של וידאו דמו למחשבון
    """
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    calculator.demo_video_url = data.demo_video_url
    await session.flush()
    await session.refresh(calculator)
    
    return calculator


@router.delete("/{calc_id}/video")
async def delete_calculator_video(
    calc_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    מחיקת וידאו דמו ממחשבון
    """
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    calculator.demo_video_url = None
    await session.flush()
    
    return {"message": f"וידאו נמחק ממחשבון {calc_id}"}


@router.post("/{calc_id}/upload-to-youtube", response_model=CalculatorResponse)
async def upload_video_to_youtube(
    calc_id: int,
    data: YouTubeUploadRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    העלאת וידאו הדמו של המחשבון ליוטיוב
    """
    import subprocess
    import os
    from pathlib import Path
    from loguru import logger
    
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    if not calculator.demo_video_url:
        raise HTTPException(status_code=400, detail="אין וידאו דמו למחשבון זה")
    
    # נתיב לקובץ הוידאו
    video_path = Path("static") / calculator.demo_video_url.lstrip("/static/")
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="קובץ הוידאו לא נמצא")
    
    # הכנת פרמטרים להעלאה
    title = data.title or f"מחשבון {calculator.name} - הדגמה"
    description = data.description or f"""
הדגמה של מחשבון {calculator.name}

קישור למחשבון: {calculator.target_url}

מחשבון זה עוזר לך לקבל הצעות מותאמות אישית!
"""
    tags = data.tags or ["מחשבון", "הלוואות", "מימון", calculator.name]
    
    # נתיב לסקריפט ההעלאה
    youtube_script = Path.home() / ".claude" / "skills" / "youtube-uploader" / "scripts" / "youtube-upload.ts"
    
    if not youtube_script.exists():
        raise HTTPException(
            status_code=500, 
            detail="סקריפט העלאה ליוטיוב לא נמצא. יש להתקין את youtube-uploader skill"
        )
    
    try:
        # בניית הפקודה
        cmd = [
            "npx", "ts-node", str(youtube_script),
            "--video", str(video_path.absolute()),
            "--title", title,
            "--description", description,
            "--tags", ",".join(tags),
            "--privacy", data.privacy
        ]
        
        logger.info(f"📺 Uploading video to YouTube: {calculator.name}")
        
        # הרצת הסקריפט
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 דקות מקסימום להעלאה
            cwd=str(youtube_script.parent)
        )
        
        if process.returncode != 0:
            logger.error(f"YouTube upload failed: {process.stderr}")
            raise HTTPException(
                status_code=500, 
                detail=f"שגיאה בהעלאה ליוטיוב: {process.stderr[:500]}"
            )
        
        # חילוץ ה-URL מהפלט
        output = process.stdout
        youtube_url = None
        
        # חיפוש URL ביוטיוב בפלט
        import re
        url_match = re.search(r'https://youtu\.be/[\w-]+|https://www\.youtube\.com/watch\?v=[\w-]+', output)
        if url_match:
            youtube_url = url_match.group(0)
        
        if youtube_url:
            calculator.youtube_url = youtube_url
            await session.flush()
            await session.refresh(calculator)
            logger.info(f"📺 ✅ Video uploaded to YouTube: {youtube_url}")
        else:
            logger.warning(f"📺 ⚠️ Could not extract YouTube URL from output: {output[:500]}")
            raise HTTPException(
                status_code=500,
                detail="הוידאו הועלה אבל לא הצלחנו לחלץ את ה-URL"
            )
        
        return calculator
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="העלאה ליוטיוב ארכה יותר מדי זמן")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"YouTube upload error: {e}")
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")


class VideoGenerateRequest(BaseModel):
    """סכמה לייצור וידאו"""
    url: str
    with_captions: bool = False  # האם להוסיף כתוביות


@router.post("/{calc_id}/generate-video", response_model=CalculatorResponse)
async def generate_calculator_video(
    calc_id: int,
    data: VideoGenerateRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    ייצור וידאו דמו למחשבון באמצעות Playwright
    """
    import subprocess
    import os
    from pathlib import Path
    from datetime import datetime
    
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    # יצירת תיקייה לוידאו אם לא קיימת
    videos_dir = Path("static/videos")
    videos_dir.mkdir(parents=True, exist_ok=True)
    
    # שם קובץ ייחודי
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = calculator.name.replace(" ", "_").replace("/", "_")[:30]
    output_filename = f"{safe_name}_{calc_id}_{timestamp}.webm"
    output_path = videos_dir / output_filename
    
    # הרצת הסקריפט
    script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "generate_calculator_video.py"
    
    try:
        # בניית הפקודה
        cmd = [
            "python", str(script_path),
            "--url", data.url,
            "--output", str(output_path)
        ]
        
        # הוספת כתוביות אם נדרש
        if data.with_captions:
            cmd.extend(["--captions", "--calc-name", calculator.name])
        
        # הרצת הסקריפט כ-subprocess
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 דקות מקסימום
        )
        
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail=f"שגיאה ביצירת וידאו: {process.stderr}")
        
        # עדכון URL בדאטאבייס
        video_url = f"/static/videos/{output_filename}"
        calculator.demo_video_url = video_url
        await session.flush()
        await session.refresh(calculator)
        
        return calculator
        
    except subprocess.TimeoutExpired:
        # בדוק אם הוידאו נוצר למרות ה-timeout
        if output_path.exists() and output_path.stat().st_size > 0:
            video_url = f"/static/videos/{output_filename}"
            calculator.demo_video_url = video_url
            await session.flush()
            await session.refresh(calculator)
            return calculator
        raise HTTPException(status_code=500, detail="ייצור הוידאו ארך יותר מדי זמן")
    except Exception as e:
        # בדוק אם הוידאו נוצר למרות השגיאה
        if output_path.exists() and output_path.stat().st_size > 0:
            video_url = f"/static/videos/{output_filename}"
            calculator.demo_video_url = video_url
            await session.flush()
            await session.refresh(calculator)
            return calculator
        raise HTTPException(status_code=500, detail=f"שגיאה: {str(e)}")


# ========== Calculator Scanning Endpoints ==========

# Global state for scan progress
CALC_SCAN_STATUS = {
    "is_running": False,
    "current_calc": None,
    "processed": 0,
    "total": 0
}


@router.get("/scan/status")
async def get_scan_status():
    """
    קבלת סטטוס סריקת מחשבונים
    """
    return CALC_SCAN_STATUS


@router.post("/scan/all")
async def scan_all_calculators(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקת כל עמודי המחשבונים ויצירת תקצירים
    """
    global CALC_SCAN_STATUS
    
    if CALC_SCAN_STATUS["is_running"]:
        return {"message": "סריקה כבר רצה", "status": CALC_SCAN_STATUS}
    
    # Get all calculators
    result = await session.execute(select(Calculator))
    calculators = result.scalars().all()
    
    CALC_SCAN_STATUS = {
        "is_running": True,
        "current_calc": None,
        "processed": 0,
        "total": len(calculators)
    }
    
    # Start background task
    import asyncio
    asyncio.create_task(run_scan_all_calculators([
        {"id": c.id, "name": c.name, "url": c.target_url}
        for c in calculators
    ]))
    
    return {
        "message": f"מתחיל סריקה של {len(calculators)} מחשבונים",
        "total": len(calculators)
    }


async def run_scan_all_calculators(calculators: list):
    """
    Background task לסריקת כל המחשבונים
    """
    global CALC_SCAN_STATUS
    from app.scraper.calculator_scraper import get_calculator_scraper
    from app.database import AsyncSessionLocal
    from loguru import logger
    
    scraper = get_calculator_scraper()
    
    async with AsyncSessionLocal() as session:
        for calc in calculators:
            try:
                CALC_SCAN_STATUS["current_calc"] = calc["name"]
                logger.info(f"📊 Scanning calculator: {calc['name']}")
                
                # Scrape and generate summary
                result = await scraper.scrape_and_summarize(
                    calc["id"],
                    calc["url"],
                    calc["name"]
                )
                
                if result["success"]:
                    # Update database
                    db_result = await session.execute(
                        select(Calculator).where(Calculator.id == calc["id"])
                    )
                    calculator = db_result.scalar_one_or_none()
                    
                    if calculator:
                        calculator.scraped_content = result["scraped_content"][:15000]
                        calculator.ai_summary = result["ai_summary"]
                        calculator.scraped_at = result["scraped_at"]
                        await session.commit()
                        logger.info(f"✅ Saved summary for: {calc['name']}")
                
                CALC_SCAN_STATUS["processed"] += 1
                
            except Exception as e:
                logger.error(f"Error scanning {calc['name']}: {e}")
                CALC_SCAN_STATUS["processed"] += 1
            
            # Small delay between requests
            import asyncio
            await asyncio.sleep(2)
    
    CALC_SCAN_STATUS["is_running"] = False
    CALC_SCAN_STATUS["current_calc"] = "הושלם ✅"
    logger.info(f"✅ Completed scanning {len(calculators)} calculators")


@router.post("/{calc_id}/scan")
async def scan_single_calculator(
    calc_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקת מחשבון בודד ויצירת תקציר
    """
    from app.scraper.calculator_scraper import get_calculator_scraper
    
    # Get calculator
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    # Scrape and summarize
    scraper = get_calculator_scraper()
    scan_result = await scraper.scrape_and_summarize(
        calculator.id,
        calculator.target_url,
        calculator.name
    )
    
    if scan_result["success"]:
        calculator.scraped_content = scan_result["scraped_content"][:15000]
        calculator.ai_summary = scan_result["ai_summary"]
        calculator.scraped_at = scan_result["scraped_at"]
        await session.commit()
    
    return {
        "calc_id": calc_id,
        "name": calculator.name,
        "ai_summary": scan_result.get("ai_summary", ""),
        "success": scan_result["success"],
        "error": scan_result.get("error")
    }


@router.get("/{calc_id}/summary")
async def get_calculator_summary(
    calc_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת תקציר מחשבון
    """
    result = await session.execute(
        select(Calculator).where(Calculator.id == calc_id)
    )
    calculator = result.scalar_one_or_none()
    
    if not calculator:
        raise HTTPException(status_code=404, detail="מחשבון לא נמצא")
    
    return {
        "calc_id": calc_id,
        "name": calculator.name,
        "ai_summary": calculator.ai_summary,
        "intent_description": calculator.intent_description,
        "scraped_at": calculator.scraped_at.isoformat() if calculator.scraped_at else None,
        "has_summary": bool(calculator.ai_summary)
    }
