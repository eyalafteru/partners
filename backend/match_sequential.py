"""
התאמת מחשבונים - קמפיין אחד אחד
"""
import asyncio
import httpx
from loguru import logger

API_URL = "http://localhost:8000"

async def wait_for_campaign(campaign_id: int):
    """מחכה שקמפיין יסיים"""
    while True:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                response = await client.get(f"{API_URL}/api/scans/{campaign_id}")
                data = response.json()
                
                status = data.get("calc_match_status")
                processed = data.get("calc_match_processed", 0)
                total = data.get("calc_match_total", 0)
                
                if status != "running":
                    print(f"  Campaign {campaign_id} finished!")
                    return
                
                print(f"  Progress: {processed}/{total}")
                await asyncio.sleep(10)
                
            except Exception as e:
                print(f"  Error checking status: {e}")
                await asyncio.sleep(5)

async def run_campaign(campaign_id: int, name: str):
    """מריץ קמפיין בודד ומחכה שיסיים"""
    print(f"\n{'='*50}")
    print(f"Starting Campaign {campaign_id}: {name}")
    print(f"{'='*50}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(f"{API_URL}/api/scans/{campaign_id}/match-calculators")
            data = response.json()
            print(f"  Started: {data.get('total', 0)} sites to match")
        except Exception as e:
            print(f"  Error starting: {e}")
            return
    
    # Wait for completion
    await wait_for_campaign(campaign_id)

async def main():
    """מריץ את כל הקמפיינים אחד אחד"""
    campaigns = [
        (1, "הלוואה לכל מטרה"),
        (2, "הלוואות לעסקים"),
        (3, "יעוץ משכנתא"),
        (4, "מימון רכב"),
        (5, "יועץ עסקי"),
    ]
    
    print("🚀 Starting sequential campaign matching...")
    
    for campaign_id, name in campaigns:
        await run_campaign(campaign_id, name)
    
    print("\n" + "="*50)
    print("🎉 All campaigns completed!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
