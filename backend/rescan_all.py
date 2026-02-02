"""
סריקה מחדש של כל האתרים ללא תוכן - רק Zenrows
"""
import asyncio
import httpx
import re
from bs4 import BeautifulSoup
from sqlalchemy import select, or_, func
from app.database import AsyncSessionLocal
from app.models.scan_campaign import ScanCampaign, ScanQueue
from loguru import logger

ZENROWS_API_KEY = "293560d128bbd0f2fdf5748fe3df4ba3b99327e2"

# URLs to skip (social media, PDFs, etc)
SKIP_PATTERNS = [
    'instagram.com', 'facebook.com', 'twitter.com', 'linkedin.com',
    'youtube.com', 'tiktok.com', '.pdf', 'knesset.gov.il'
]

async def scrape_with_zenrows(url: str) -> dict:
    """סריקה עם Zenrows בלבד"""
    # Skip problematic URLs
    if any(pattern in url.lower() for pattern in SKIP_PATTERNS):
        return {"error": f"Skipped: {url}", "inner_text": ""}
    
    try:
        api_url = "https://api.zenrows.com/v1/"
        params = {
            "apikey": ZENROWS_API_KEY,
            "url": url,
            "js_render": "true",
            "premium_proxy": "true",
            "proxy_country": "il"
        }
        
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.get(api_url, params=params)
            
            if response.status_code != 200:
                return {"error": f"Zenrows {response.status_code}", "inner_text": ""}
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else ""
            
            # Extract text
            if soup.body:
                for element in soup.body(['script', 'style', 'noscript']):
                    element.decompose()
                inner_text = soup.body.get_text(separator=' ', strip=True)[:15000]
            else:
                inner_text = ""
            
            # Extract emails
            emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
            emails = [e for e in set(emails) if 'wix' not in e.lower() and 'example' not in e.lower()][:5]
            
            # Extract phones
            phones = re.findall(r'0[23489]-?\d{7}|05[0-9]-?\d{7}', html)
            phones = list(set(phones))[:5]
            
            return {
                "html": html[:50000],
                "inner_text": inner_text,
                "title": title,
                "emails": emails,
                "phones": phones,
                "error": None
            }
    except Exception as e:
        return {"error": str(e), "inner_text": ""}

async def rescan_campaign(campaign_id: int):
    """סריקה מחדש של קמפיין בודד"""
    
    async with AsyncSessionLocal() as session:
        # Get campaign name
        result = await session.execute(
            select(ScanCampaign).where(ScanCampaign.id == campaign_id)
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            print(f"Campaign {campaign_id} not found")
            return
        
        print(f"\n{'='*50}")
        print(f"Campaign {campaign_id}: {campaign.name}")
        print(f"{'='*50}")
        
        # Get items without content
        result = await session.execute(
            select(ScanQueue)
            .where(ScanQueue.campaign_id == campaign_id)
            .where(or_(
                ScanQueue.html_text == None,
                func.length(ScanQueue.html_text) < 100
            ))
        )
        items = result.scalars().all()
        
        total = len(items)
        if total == 0:
            print(f"All sites have content!")
            return
        
        print(f"Found {total} sites without content")
        success = 0
        
        for idx, item in enumerate(items, 1):
            print(f"\n[{idx}/{total}] Scraping: {item.url}")
            
            try:
                # Use Zenrows only
                scrape_result = await scrape_with_zenrows(item.url)
                
                if scrape_result and not scrape_result.get("error"):
                    content_len = len(scrape_result.get("inner_text", ""))
                    if content_len > 100:
                        item.html_body = scrape_result.get("html", "")[:50000]
                        item.html_text = scrape_result.get("inner_text", "")[:15000]
                        item.title = scrape_result.get("title", item.title)
                        
                        if scrape_result.get("emails"):
                            item.emails_found = scrape_result["emails"]
                        if scrape_result.get("phones"):
                            item.phones_found = scrape_result["phones"]
                        
                        await session.commit()
                        success += 1
                        print(f"   ✅ Got {content_len} chars")
                    else:
                        print(f"   ⚠️ Content too short: {content_len} chars")
                else:
                    error = scrape_result.get("error", "Unknown") if scrape_result else "No result"
                    print(f"   ❌ {error}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Small delay between requests
            await asyncio.sleep(1)
        
        print(f"\n✅ Campaign {campaign_id} done: {success}/{total} successful")

async def main():
    """סריקה מחדש של כל הקמפיינים"""
    print("🔄 Starting full rescan of all campaigns...")
    
    # Get all campaign IDs
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(ScanCampaign.id, ScanCampaign.name))
        campaigns = result.all()
    
    for campaign_id, name in campaigns:
        await rescan_campaign(campaign_id)
    
    print("\n" + "="*50)
    print("🎉 All campaigns rescanned!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
