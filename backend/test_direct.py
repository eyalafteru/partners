"""Test AI directly with real content"""
import asyncio
import httpx

async def test():
    # Simple test prompt
    prompt = """בחר מחשבון מתאים לאתר.

אתר:
=== כותרת ===
הלוואה חוץ בנקאית מיידית - בדקו זכאות! - המרכז להבראה פיננסית

=== תיאור ===
הלוואה חוץ בנקאית מיידית לכל לקוחות הבנקים

מחשבונים זמינים:
[{"id": 1, "name": "מחשבון משכנתא"}, {"id": 2, "name": "מחשבון הלוואה"}]

החזר JSON בלבד:
{"calc_id": 2, "match_score": 0.9, "reasoning": "הסבר קצר", "suggested_new_calc": null}"""

    payload = {
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": prompt,
        "system": "השב JSON בלבד. ללא הסברים.",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 300}
    }
    
    print("Calling AI...")
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post("http://localhost:11434/api/generate", json=payload)
        result = response.json()
        
    raw = result.get("response", "")
    print(f"Response ({len(raw)} chars):")
    print(raw[:500])
    print()
    
    # Unload
    await client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "",
        "keep_alive": "0"
    })
    print("Model unloaded")

if __name__ == "__main__":
    asyncio.run(test())
