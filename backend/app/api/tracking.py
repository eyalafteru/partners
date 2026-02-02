"""
PartnerCalc OS - Email Tracking API
מעקב פתיחות וקליקים במיילים
"""
from fastapi import APIRouter, Depends, Response, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from loguru import logger
import base64
import hashlib

from app.database import get_async_session
from app.models.communication import Communication

router = APIRouter()

# 1x1 transparent GIF pixel
TRACKING_PIXEL = base64.b64decode(
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)


def generate_tracking_id(communication_id: int, secret: str = "partnercalc") -> str:
    """יצירת מזהה מעקב מוצפן"""
    data = f"{communication_id}:{secret}"
    return base64.urlsafe_b64encode(
        hashlib.sha256(data.encode()).digest()[:12] + 
        str(communication_id).encode()
    ).decode().rstrip("=")


def decode_tracking_id(tracking_id: str) -> int:
    """פענוח מזהה מעקב"""
    try:
        # הוספת padding אם חסר
        padding = 4 - len(tracking_id) % 4
        if padding != 4:
            tracking_id += "=" * padding
        
        decoded = base64.urlsafe_b64decode(tracking_id)
        # ה-communication_id נמצא אחרי 12 הבייטים הראשונים
        comm_id_bytes = decoded[12:]
        return int(comm_id_bytes.decode())
    except Exception as e:
        logger.error(f"Failed to decode tracking ID: {e}")
        return None


@router.get("/pixel/{tracking_id}.gif")
async def track_open(
    tracking_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Tracking Pixel - נטען כשהמייל נפתח
    מחזיר תמונה שקופה 1x1
    """
    try:
        comm_id = decode_tracking_id(tracking_id)
        
        if comm_id:
            # עדכון הפתיחה
            result = await session.execute(
                select(Communication).where(Communication.id == comm_id)
            )
            comm = result.scalar_one_or_none()
            
            if comm:
                # עדכון ספירת פתיחות
                comm.opens_count = (comm.opens_count or 0) + 1
                
                # סימון כנקרא בפעם הראשונה
                if not comm.read_at:
                    comm.read_at = datetime.utcnow()
                    comm.status = "read"
                
                await session.commit()
                logger.info(f"📧 Email opened: comm_id={comm_id}, opens={comm.opens_count}")
    
    except Exception as e:
        logger.error(f"Track open error: {e}")
    
    # תמיד מחזיר את הפיקסל
    return Response(
        content=TRACKING_PIXEL,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.get("/click/{tracking_id}")
async def track_click(
    tracking_id: str,
    url: str = Query(..., description="URL יעד"),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Link Tracking - מפנה ליעד ושומר את הקליק
    """
    try:
        comm_id = decode_tracking_id(tracking_id)
        
        if comm_id:
            result = await session.execute(
                select(Communication).where(Communication.id == comm_id)
            )
            comm = result.scalar_one_or_none()
            
            if comm:
                # שמירת הקליק
                clicks = comm.clicks or []
                clicks.append({
                    "url": url,
                    "timestamp": datetime.utcnow().isoformat()
                })
                comm.clicks = clicks
                
                await session.commit()
                logger.info(f"📧 Link clicked: comm_id={comm_id}, url={url}")
    
    except Exception as e:
        logger.error(f"Track click error: {e}")
    
    # הפניה ליעד
    return RedirectResponse(url=url, status_code=302)


@router.get("/stats/{communication_id}")
async def get_tracking_stats(
    communication_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    קבלת סטטיסטיקות מעקב למייל
    """
    result = await session.execute(
        select(Communication).where(Communication.id == communication_id)
    )
    comm = result.scalar_one_or_none()
    
    if not comm:
        return {"error": "Communication not found"}
    
    return {
        "communication_id": communication_id,
        "status": comm.status,
        "opens_count": comm.opens_count or 0,
        "first_opened_at": comm.read_at.isoformat() if comm.read_at else None,
        "clicks": comm.clicks or [],
        "clicks_count": len(comm.clicks or [])
    }
