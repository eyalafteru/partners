"""בדיקה מה נמצא בדאטאבייס של הסיפור"""
import asyncio
from app.database import AsyncSessionLocal
from app.models.eyal_story import EyalStory
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(EyalStory).where(EyalStory.id == 1))
        story = result.scalar_one_or_none()
        if story:
            print("=== STORY CONTENT ===")
            print(f"Length: {len(story.story_content or '')} chars")
            print()
            print((story.story_content or '')[:2000])
            print()
            print("=== FORBIDDEN PHRASES ===")
            print(story.forbidden_phrases or "None")
            print()
            print("=== AI INSTRUCTIONS ===")
            print(story.ai_instructions or "None")
        else:
            print("No story found!")

if __name__ == "__main__":
    asyncio.run(check())
