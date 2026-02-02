"""
PartnerCalc OS - Stats API
סטטיסטיקות ל-Control Center
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_async_session
from app.models.lead import Lead
from app.models.communication import Communication
from app.models.installation import Installation
from app.models.scan_campaign import ScanCampaign

router = APIRouter()


@router.get("/overview")
async def get_overview(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סטטיסטיקות כלליות ל-Control Center
    """
    # סה"כ נסרקו
    result = await session.execute(select(func.count(Lead.id)))
    total_scanned = result.scalar()
    
    # נמצאה התאמה
    result = await session.execute(
        select(func.count(Lead.id))
        .where(Lead.status.in_(["matched", "contacted", "responded", "installed"]))
    )
    total_matched = result.scalar()
    
    # נשלחה פנייה
    result = await session.execute(
        select(func.count(Communication.id))
        .where(Communication.direction == "outbound")
    )
    total_sent = result.scalar()
    
    # התקנות פעילות
    result = await session.execute(
        select(func.count(Installation.id))
        .where(Installation.is_link_live == True)
    )
    total_installations = result.scalar()
    
    return {
        "scanned": total_scanned,
        "matched": total_matched,
        "sent": total_sent,
        "installations": total_installations
    }


@router.get("/funnel")
async def get_funnel(
    session: AsyncSession = Depends(get_async_session)
):
    """
    נתוני Funnel - מסלול ההמרה
    """
    # ספירה לפי סטטוס
    result = await session.execute(
        select(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
    )
    status_counts = {row[0]: row[1] for row in result.all()}
    
    # חישוב אחוזים
    total = sum(status_counts.values())
    
    funnel = [
        {
            "stage": "נסרקו",
            "count": total,
            "percent": 100
        },
        {
            "stage": "התאמה",
            "count": status_counts.get("matched", 0) + status_counts.get("contacted", 0) + 
                     status_counts.get("responded", 0) + status_counts.get("installed", 0),
            "percent": 0
        },
        {
            "stage": "נשלח",
            "count": status_counts.get("contacted", 0) + status_counts.get("responded", 0) + 
                     status_counts.get("installed", 0),
            "percent": 0
        },
        {
            "stage": "התקנה",
            "count": status_counts.get("installed", 0),
            "percent": 0
        }
    ]
    
    # חישוב אחוזים
    for stage in funnel:
        stage["percent"] = round((stage["count"] / total * 100), 1) if total > 0 else 0
    
    return funnel


@router.get("/by-channel")
async def get_by_channel(
    session: AsyncSession = Depends(get_async_session)
):
    """
    פילוח לפי ערוץ תקשורת
    """
    # הודעות יוצאות לפי ערוץ
    result = await session.execute(
        select(Communication.channel, func.count(Communication.id))
        .where(Communication.direction == "outbound")
        .group_by(Communication.channel)
    )
    sent_by_channel = {row[0]: row[1] for row in result.all()}
    
    # תגובות לפי ערוץ
    result = await session.execute(
        select(Communication.channel, func.count(Communication.id))
        .where(Communication.direction == "inbound")
        .group_by(Communication.channel)
    )
    responses_by_channel = {row[0]: row[1] for row in result.all()}
    
    channels = ["whatsapp", "email", "sms"]
    
    return [
        {
            "channel": channel,
            "sent": sent_by_channel.get(channel, 0),
            "responses": responses_by_channel.get(channel, 0),
            "response_rate": round(
                (responses_by_channel.get(channel, 0) / sent_by_channel.get(channel, 1) * 100), 1
            ) if sent_by_channel.get(channel, 0) > 0 else 0
        }
        for channel in channels
    ]


@router.get("/active-scans")
async def get_active_scans(
    session: AsyncSession = Depends(get_async_session)
):
    """
    סריקות פעילות כרגע
    """
    result = await session.execute(
        select(ScanCampaign)
        .where(ScanCampaign.status == "running")
        .order_by(ScanCampaign.started_at.desc())
    )
    campaigns = result.scalars().all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "total_urls": c.total_urls or 0,
            "scanned_count": c.scanned_count or 0,
            "matched_count": c.matched_count or 0,
            "progress_percent": c.progress_percent
        }
        for c in campaigns
    ]


@router.get("/timeline")
async def get_timeline(
    days: int = 7,
    session: AsyncSession = Depends(get_async_session)
):
    """
    נתונים לגרף לפי ימים
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # לידים חדשים לפי יום
    result = await session.execute(
        select(
            func.date(Lead.created_at).label("date"),
            func.count(Lead.id).label("count")
        )
        .where(Lead.created_at >= start_date)
        .group_by(func.date(Lead.created_at))
        .order_by(func.date(Lead.created_at))
    )
    leads_by_day = {str(row[0]): row[1] for row in result.all()}
    
    # התקנות לפי יום
    result = await session.execute(
        select(
            func.date(Installation.installed_at).label("date"),
            func.count(Installation.id).label("count")
        )
        .where(Installation.installed_at >= start_date)
        .group_by(func.date(Installation.installed_at))
        .order_by(func.date(Installation.installed_at))
    )
    installs_by_day = {str(row[0]): row[1] for row in result.all()}
    
    # יצירת רשימה מלאה של תאריכים
    timeline = []
    for i in range(days):
        date = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        timeline.append({
            "date": date,
            "leads": leads_by_day.get(date, 0),
            "installations": installs_by_day.get(date, 0)
        })
    
    return timeline


@router.get("/top-calculators")
async def get_top_calculators(
    limit: int = 5,
    session: AsyncSession = Depends(get_async_session)
):
    """
    המחשבונים עם הכי הרבה התקנות
    """
    from app.models.calculator import Calculator
    
    result = await session.execute(
        select(
            Calculator.id,
            Calculator.name,
            func.count(Installation.id).label("installs")
        )
        .join(Installation, Calculator.id == Installation.calc_id)
        .where(Installation.is_link_live == True)
        .group_by(Calculator.id, Calculator.name)
        .order_by(func.count(Installation.id).desc())
        .limit(limit)
    )
    
    return [
        {"id": row[0], "name": row[1], "installations": row[2]}
        for row in result.all()
    ]
