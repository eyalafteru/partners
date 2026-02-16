"""
PartnerCalc OS - Facebook Marketing Background Tasks
Tasks רקע לניהול פרסום בקבוצות פייסבוק
"""
import asyncio
from datetime import datetime, timedelta
from typing import List
from loguru import logger
from sqlalchemy import select, and_, or_, func

from app.database import get_async_session_context
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
FIRST_COMMENT_INTERVAL = 120  # 2 דקות - בדיקת תגובות ראשונות
AUTO_RESPOND_INTERVAL = 300  # 5 דקות - תשובות אוטומטיות


async def sync_all_post_comments():
    """
    סנכרון תגובות מכל הפוסטים שפורסמו
    """
    try:
        async with get_async_session_context() as session:
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
        async with get_async_session_context() as session:
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
    כולל שחזור פוסטים תקועים בסטטוס publishing
    """
    try:
        async with get_async_session_context() as session:
            # שחזור פוסטים תקועים בסטטוס "publishing" יותר מ-10 דקות
            ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
            stuck_result = await session.execute(
                select(FacebookPost).where(
                    and_(
                        FacebookPost.status == "publishing",
                        func.coalesce(FacebookPost.updated_at, FacebookPost.created_at) < ten_minutes_ago
                    )
                )
            )
            stuck_posts = stuck_result.scalars().all()
            
            if stuck_posts:
                logger.warning(f"🔄 Found {len(stuck_posts)} posts stuck in 'publishing' state, resetting to 'approved'")
                for stuck_post in stuck_posts:
                    stuck_post.status = "approved"
                    stuck_post.publish_error = "Reset: was stuck in publishing state for over 10 minutes"
                    logger.info(f"🔄 Reset post {stuck_post.id} from 'publishing' back to 'approved'")
                await session.flush()
            
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


async def post_first_comments():
    """
    פרסום תגובות ראשונות לפוסטים חדשים
    מחפש פוסטים שפורסמו ויש להם תוכן תגובה ראשונה אבל עדיין לא נשלחה
    """
    try:
        async with get_async_session_context() as session:
            from app.services.auto_responder_service import get_auto_responder_service
            
            service = get_auto_responder_service(session)
            posts = await service.get_posts_needing_first_comment()
            
            if not posts:
                return
            
            logger.info(f"💬 Posting first comments for {len(posts)} posts...")
            
            posted_count = 0
            for post in posts:
                try:
                    success = await service.post_first_comment(post.id)
                    if success:
                        posted_count += 1
                    # השהייה בין פוסטים למניעת חסימה
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.error(f"Error posting first comment for post {post.id}: {e}")
            
            await session.commit()
            
            if posted_count > 0:
                logger.info(f"💬 ✅ Posted {posted_count} first comments")
                
    except Exception as e:
        logger.error(f"💬 ❌ First comment error: {e}")


async def auto_respond_to_comments():
    """
    תשובות אוטומטיות לתגובות על פוסטים
    מחפש קמפיינים עם Auto-Responder פעיל ושולח תשובות
    """
    try:
        async with get_async_session_context() as session:
            from app.services.auto_responder_service import get_auto_responder_service
            from app.models.facebook_marketing import FacebookCampaign
            
            # מציאת קמפיינים עם auto-responder פעיל
            result = await session.execute(
                select(FacebookCampaign).where(
                    and_(
                        FacebookCampaign.auto_responder_enabled == True,
                        FacebookCampaign.status.in_(["ready", "publishing", "completed"])
                    )
                )
            )
            campaigns = result.scalars().all()
            
            if not campaigns:
                return
            
            logger.info(f"🤖 Checking auto-respond for {len(campaigns)} campaigns...")
            
            service = get_auto_responder_service(session)
            total_responses = 0
            
            for campaign in campaigns:
                try:
                    count = await service.check_and_respond_to_comments(campaign.id)
                    total_responses += count
                except Exception as e:
                    logger.error(f"Error auto-responding for campaign {campaign.id}: {e}")
            
            await session.commit()
            
            if total_responses > 0:
                logger.info(f"🤖 ✅ Sent {total_responses} auto-responses")
                
    except Exception as e:
        logger.error(f"🤖 ❌ Auto-respond error: {e}")


async def start_first_comment_task():
    """
    התחלת task תגובות ראשונות
    רץ ברקע ומפרסם תגובות ראשונות לפוסטים חדשים
    """
    logger.info("💬 Facebook First Comment Task started")
    
    while True:
        try:
            await post_first_comments()
        except Exception as e:
            logger.error(f"💬 First comment task error: {e}")
        
        await asyncio.sleep(FIRST_COMMENT_INTERVAL)


async def start_auto_responder_task():
    """
    התחלת task תשובות אוטומטיות
    רץ ברקע ושולח תשובות למגיבים
    """
    logger.info("🤖 Facebook Auto-Responder Task started")
    
    while True:
        try:
            await auto_respond_to_comments()
        except Exception as e:
            logger.error(f"🤖 Auto-responder task error: {e}")
        
        await asyncio.sleep(AUTO_RESPOND_INTERVAL)


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
        start_first_comment_task(),
        start_auto_responder_task(),
        return_exceptions=True
    )
