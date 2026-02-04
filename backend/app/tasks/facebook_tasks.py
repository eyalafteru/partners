"""
PartnerCalc OS - Facebook Marketing Background Tasks
Tasks רקע לניהול פרסום בקבוצות פייסבוק
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from loguru import logger
from sqlalchemy import select, and_

from app.database import async_session_maker
from app.models.facebook_marketing import (
    FacebookPost,
    FacebookReply,
    FacebookConversation
)
from app.services.facebook_marketing_service import get_facebook_marketing_service
from app.services.facebook_reply_service import get_facebook_reply_service
from app.services.apify_service import get_apify_service


# הגדרות
COMMENT_SYNC_INTERVAL = 300  # 5 דקות
RESPONSE_GENERATION_INTERVAL = 60  # דקה
PUBLISH_CHECK_INTERVAL = 120  # 2 דקות


async def sync_all_post_comments():
    """
    סנכרון תגובות מכל הפוסטים שפורסמו
    """
    try:
        async with async_session_maker() as session:
            # מציאת פוסטים שפורסמו בשבוע האחרון
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            result = await session.execute(
                select(FacebookPost).where(
                    and_(
                        FacebookPost.status == "published",
                        FacebookPost.published_at >= week_ago,
                        FacebookPost.fb_post_url != None
                    )
                )
            )
            posts = result.scalars().all()
            
            if not posts:
                return
            
            logger.info(f"📥 Syncing comments for {len(posts)} posts...")
            
            service = get_facebook_marketing_service(session)
            total_new = 0
            
            for post in posts:
                try:
                    new_replies = await service.sync_post_comments(post.id)
                    total_new += len(new_replies)
                except Exception as e:
                    logger.error(f"Error syncing post {post.id}: {e}")
            
            await session.commit()
            
            if total_new > 0:
                logger.info(f"📥 ✅ Synced {total_new} new comments total")
                
    except Exception as e:
        logger.error(f"📥 ❌ Comment sync error: {e}")


async def generate_pending_responses():
    """
    יצירת תשובות AI לתגובות חדשות
    """
    try:
        async with async_session_maker() as session:
            # מציאת תגובות שצריכות תשובה
            result = await session.execute(
                select(FacebookReply).where(
                    FacebookReply.status == "new"
                ).limit(10)  # מקסימום 10 בכל פעם
            )
            replies = result.scalars().all()
            
            if not replies:
                return
            
            logger.info(f"🤖 Generating responses for {len(replies)} replies...")
            
            service = get_facebook_marketing_service(session)
            
            for reply in replies:
                try:
                    await service.generate_reply_response(reply.id)
                except Exception as e:
                    logger.error(f"Error generating response for reply {reply.id}: {e}")
            
            await session.commit()
            logger.info(f"🤖 ✅ Generated responses")
            
    except Exception as e:
        logger.error(f"🤖 ❌ Response generation error: {e}")


async def check_scheduled_posts():
    """
    בדיקת פוסטים מתוזמנים לפרסום
    """
    try:
        async with async_session_maker() as session:
            # מציאת פוסטים מאושרים שמחכים לפרסום
            result = await session.execute(
                select(FacebookPost).where(
                    FacebookPost.status == "approved"
                ).limit(5)
            )
            posts = result.scalars().all()
            
            if not posts:
                return
            
            logger.info(f"📤 Publishing {len(posts)} approved posts...")
            
            service = get_facebook_marketing_service(session)
            
            for post in posts:
                try:
                    await service.publish_post(post.id)
                    # השהייה בין פוסטים למניעת חסימה
                    await asyncio.sleep(60)
                except Exception as e:
                    logger.error(f"Error publishing post {post.id}: {e}")
            
            await session.commit()
            
    except Exception as e:
        logger.error(f"📤 ❌ Scheduled posts error: {e}")


async def start_comment_monitor():
    """
    התחלת מוניטור תגובות
    רץ ברקע ומסנכרן תגובות מדי כמה דקות
    """
    logger.info("🔄 Facebook Comment Monitor started")
    
    while True:
        try:
            # סנכרון תגובות
            await sync_all_post_comments()
            
        except Exception as e:
            logger.error(f"🔄 Comment monitor error: {e}")
        
        await asyncio.sleep(COMMENT_SYNC_INTERVAL)


async def start_response_generator():
    """
    התחלת מחולל תשובות
    רץ ברקע ומייצר תשובות AI לתגובות חדשות
    """
    logger.info("🤖 Facebook Response Generator started")
    
    while True:
        try:
            # יצירת תשובות
            await generate_pending_responses()
            
        except Exception as e:
            logger.error(f"🤖 Response generator error: {e}")
        
        await asyncio.sleep(RESPONSE_GENERATION_INTERVAL)


async def start_publish_scheduler():
    """
    התחלת מתזמן פרסום
    רץ ברקע ומפרסם פוסטים מאושרים
    """
    logger.info("📤 Facebook Publish Scheduler started")
    
    while True:
        try:
            # בדיקת פוסטים לפרסום
            await check_scheduled_posts()
            
        except Exception as e:
            logger.error(f"📤 Publish scheduler error: {e}")
        
        await asyncio.sleep(PUBLISH_CHECK_INTERVAL)


async def start_facebook_tasks():
    """
    התחלת כל ה-tasks של פייסבוק
    """
    logger.info("📘 Starting Facebook Marketing Tasks...")
    
    # הרצת כל ה-tasks במקביל
    await asyncio.gather(
        start_comment_monitor(),
        start_response_generator(),
        start_publish_scheduler(),
        return_exceptions=True
    )
