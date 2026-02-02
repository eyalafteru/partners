import asyncio
from app.scraper.smart_scraper import get_smart_scraper

async def test():
    scraper = get_smart_scraper()
    print("Testing Zenrows with IL proxy...")
    result = await scraper._try_zenrows('https://israelpost.co.il/')
    if result:
        title = result.get("title", "N/A")
        print(f"✅ Success!")
        print(f"   Title: {title[:60] if title else 'N/A'}")
        print(f"   Emails: {result.get('emails', [])}")
        print(f"   Phones: {result.get('phones', [])}")
        print(f"   HTML length: {len(result.get('html', ''))}")
    else:
        print("❌ Failed")

asyncio.run(test())
