"""Test full GPT matching time (summary + GPT)"""
import asyncio
import time
from app.ai.calculator_matcher import get_calculator_matcher
import sqlite3

async def test_full_flow():
    matcher = get_calculator_matcher()
    
    # Get calculators
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, intent_description, ai_summary FROM calculators WHERE is_active = 1 LIMIT 25")
    calculators = [{"id": r[0], "name": r[1], "intent_description": r[2] or "", "ai_summary": r[3] or ""} for r in cursor.fetchall()]
    
    # Get real content
    cursor.execute("SELECT domain, html_text FROM scan_queue WHERE LENGTH(html_text) > 3000 AND gpt_recommended_calc_id IS NULL LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        print("No sites to test")
        return
    
    domain = row[0]
    content = row[1]
    
    print(f'Testing domain: {domain}')
    print(f'Content length: {len(content)} chars')
    print(f'Calculators: {len(calculators)}')
    print()
    print('Starting full GPT match flow...')
    print()
    
    total_start = time.time()
    
    result = await matcher.match_calculator_gpt(
        site_content=content,
        business_type="unknown",
        calculators=calculators
    )
    
    total_duration = time.time() - total_start
    
    print(f'')
    print(f'=== RESULTS ===')
    print(f'Total time: {total_duration:.2f} seconds')
    print(f'GPT API time: {result.get("duration_seconds", 0):.2f} seconds')
    print(f'Summary time (estimated): {total_duration - result.get("duration_seconds", 0):.2f} seconds')
    print(f'Matched calc_id: {result.get("calc_id")}')
    print(f'Score: {result.get("match_score")}')
    print(f'Reason: {result.get("reasoning", "")[:200]}...')

if __name__ == "__main__":
    asyncio.run(test_full_flow())
