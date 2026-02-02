"""Test calculator matcher"""
import asyncio
import json

async def test():
    from app.ai.ollama_client import get_ollama_client
    ollama = get_ollama_client()
    
    prompt = """בחר מחשבון מתאים לאתר הזה:
תוכן: אתר הלוואות לעסקים קטנים
מחשבונים זמינים:
[{"id": 1, "name": "מחשבון הלוואה לעסק"}]

השב בפורמט JSON בלבד:
{"calc_id": 1, "calc_name": "שם", "match_score": 0.8, "reasoning": "הסבר"}"""
    
    print("Sending to AI...")
    result = await ollama.generate(
        system_prompt="השב תמיד ב-JSON תקין בעברית",
        user_prompt=prompt,
        temperature=0.3,
        max_tokens=300
    )
    print("=" * 50)
    print("Raw Response:")
    print(result)
    print("=" * 50)
    
    # Try to parse
    import re
    json_match = re.search(r'\{[\s\S]*\}', result)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            print("Parsed JSON:", json.dumps(parsed, ensure_ascii=False, indent=2))
        except:
            print("Failed to parse JSON")
    else:
        print("No JSON found in response")

if __name__ == "__main__":
    asyncio.run(test())
