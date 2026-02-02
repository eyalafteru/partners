"""Test matching with real data from clalbit.co.il"""
import asyncio
import sqlite3
import json

async def test():
    from app.ai.calculator_matcher import get_calculator_matcher
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.calculator import Calculator
    
    # Get site content from DB
    c = sqlite3.connect('partnercalc.db').cursor()
    c.execute('''
        SELECT domain, nav_links, meta_title, meta_description, html_text, business_type
        FROM scan_queue 
        WHERE domain = 'clalbit.co.il'
    ''')
    r = c.fetchone()
    
    if not r:
        print("Site not found!")
        return
    
    domain, nav_links, meta_title, meta_description, html_text, business_type = r
    
    # Build content like in scans.py
    content_parts = []
    
    if nav_links:
        try:
            nav_data = json.loads(nav_links)
            nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
            if nav_texts:
                content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
        except:
            pass
    
    if meta_title:
        content_parts.append(f"=== כותרת ===\n{meta_title}")
    if meta_description:
        content_parts.append(f"=== תיאור ===\n{meta_description}")
    if html_text:
        content_parts.append(f"=== תוכן העמוד ===\n{html_text[:3000]}")
    
    site_content = "\n\n".join(content_parts)[:6000]
    
    print(f"Site: {domain}")
    print(f"Business type: {business_type}")
    print(f"Content length: {len(site_content)}")
    print()
    
    # Get calculators
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Calculator).where(Calculator.is_active == True).limit(5))
        calculators = [
            {"id": c.id, "name": c.name, "category": c.category, "intent_description": c.intent_description, "ai_summary": c.ai_summary, "keywords": c.keywords}
            for c in result.scalars().all()
        ]
    
    print(f"Calculators: {[c['name'] for c in calculators]}")
    print()
    
    # Match
    matcher = get_calculator_matcher()
    print("Calling matcher...")
    result = await matcher.match_calculator(site_content, business_type or "lead_site", calculators)
    
    print("=" * 60)
    print("MATCH RESULT:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
