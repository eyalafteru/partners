"""Debug - check what content is being sent to AI"""
import asyncio
import json

async def debug():
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.scan_campaign import ScanQueue
    
    async with AsyncSessionLocal() as session:
        # Get one item
        result = await session.execute(
            select(ScanQueue)
            .where(ScanQueue.campaign_id == 1)
            .where(ScanQueue.business_type.in_(["lead_site", "small_business"]))
            .where(ScanQueue.html_text != None)
            .limit(1)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            print("No items found!")
            return
        
        print(f"=== Domain: {item.domain} ===")
        print(f"Business Type: {item.business_type}")
        print()
        
        # Build content like in scans.py
        content_parts = []
        
        # Navigation
        if item.nav_links:
            try:
                nav_data = json.loads(item.nav_links)
                nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
                if nav_texts:
                    content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
                    print(f"✅ Nav links: {len(nav_texts)} items")
            except Exception as e:
                print(f"❌ Nav links error: {e}")
        else:
            print("❌ No nav_links")
        
        # Meta
        if item.meta_title:
            content_parts.append(f"=== כותרת ===\n{item.meta_title}")
            print(f"✅ Meta title: {item.meta_title[:50]}...")
        else:
            print("❌ No meta_title")
            
        if item.meta_description:
            content_parts.append(f"=== תיאור ===\n{item.meta_description}")
            print(f"✅ Meta description: {item.meta_description[:50]}...")
        else:
            print("❌ No meta_description")
        
        # HTML content
        if item.html_text:
            content_parts.append(f"=== תוכן העמוד ===\n{item.html_text[:3000]}")
            print(f"✅ HTML text: {len(item.html_text)} chars")
        else:
            print("❌ No html_text")
        
        # Calculator in menu
        if item.has_menu_calculator:
            content_parts.append("=== מידע נוסף ===\nיש קישור למחשבון בתפריט הראשי")
            print("✅ Has menu calculator")
        
        site_content = "\n\n".join(content_parts)[:6000]
        
        print()
        print(f"=== FINAL CONTENT ({len(site_content)} chars) ===")
        print(site_content[:2000])
        print("...")

if __name__ == "__main__":
    asyncio.run(debug())
