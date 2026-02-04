"""Script to create Facebook Marketing tables"""
import asyncio
from loguru import logger

# Import all models to register them with Base
from app.models import (
    FacebookGroup, FacebookCampaign, FacebookPost, FacebookReply,
    FacebookConversation, FacebookMessage, FacebookPostTemplate
)
from app.database import init_db

async def main():
    logger.info("Creating Facebook Marketing tables...")
    await init_db()
    print("Tables created!")

if __name__ == "__main__":
    asyncio.run(main())
