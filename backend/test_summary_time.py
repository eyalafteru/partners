"""Test summarization timing"""
import asyncio
import time
from app.ai.calculator_matcher import get_calculator_matcher
import sqlite3

async def test_with_timing():
    matcher = get_calculator_matcher()
    
    # Get real content
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    cursor.execute("SELECT html_text FROM scan_queue WHERE LENGTH(html_text) > 3000 LIMIT 1")
    row = cursor.fetchone()
    content = row[0] if row else ''
    conn.close()
    
    print(f'Content length: {len(content)} chars')
    print(f'MAX_CONTENT_FOR_DIRECT_MATCH: {matcher.MAX_CONTENT_FOR_DIRECT_MATCH}')
    print(f'Will summarize: {len(content) > matcher.MAX_CONTENT_FOR_DIRECT_MATCH}')
    print()
    print('Testing summarization with Ollama gemma2:9b...')
    
    start = time.time()
    summary = await matcher._summarize_content(content)
    duration = time.time() - start
    
    print(f'')
    print(f'=== RESULTS ===')
    print(f'Summary time: {duration:.2f} seconds')
    print(f'Summary length: {len(summary)} chars')
    print(f'Summary: {summary[:300]}...')

if __name__ == "__main__":
    asyncio.run(test_with_timing())
