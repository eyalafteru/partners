"""
Watchdog Tasks - מנגנון שמנטר ומאפס תהליכים תקועים
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.scan_campaign import ScanCampaign


async def check_stuck_processes():
    """
    בודק ומאפס תהליכים תקועים
    """
    try:
        async for session in get_async_session():
            # Find campaigns with stuck AI processes (running for more than 10 minutes)
            ten_mins_ago = datetime.utcnow() - timedelta(minutes=10)
            
            # Check for stuck AI processes
            result = await session.execute(
                select(ScanCampaign).where(
                    ScanCampaign.ai_current_domain.isnot(None)
                )
            )
            campaigns = result.scalars().all()
            
            reset_count = 0
            for campaign in campaigns:
                # If AI is "running" but updated_at is old, it's stuck
                if campaign.updated_at and campaign.updated_at < ten_mins_ago:
                    logger.warning(
                        f"🐕 Watchdog: Resetting stuck AI process for campaign {campaign.id} ({campaign.name}) - stuck for 10+ minutes"
                    )
                    campaign.ai_current_domain = None
                    campaign.ai_processed = 0
                    campaign.ai_total = 0
                    reset_count += 1
                
                # Also check for stuck rescan status
                if campaign.rescan_status and campaign.updated_at and campaign.updated_at < ten_mins_ago:
                    logger.warning(
                        f"🐕 Watchdog: Resetting stuck rescan for campaign {campaign.id} ({campaign.name}) - stuck for 10+ minutes"
                    )
                    campaign.rescan_status = None
                    campaign.rescan_processed = 0
                    campaign.rescan_total = 0
                    reset_count += 1
            
            if reset_count > 0:
                await session.commit()
                logger.info(f"🐕 Watchdog: Reset {reset_count} stuck processes - Dashboard will update automatically")
            
            break  # Exit after first session
            
    except Exception as e:
        logger.error(f"🐕 Watchdog error: {e}")


async def start_watchdog():
    """
    מפעיל את ה-watchdog - רץ כל 30 שניות
    """
    logger.info("🐕 Watchdog task started - checking every 30 seconds for stuck processes")
    
    while True:
        try:
            await asyncio.sleep(30)  # Wait 30 seconds - much faster response!
            await check_stuck_processes()
        except asyncio.CancelledError:
            logger.info("🐕 Watchdog task cancelled")
            break
        except Exception as e:
            logger.error(f"🐕 Watchdog task error: {e}")
            await asyncio.sleep(30)  # Wait 30 seconds on error
