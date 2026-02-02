"""Debug AI response"""
import asyncio
import re

async def test():
    from app.ai.ollama_client import get_ollama_client
    
    ollama = get_ollama_client()
    
    prompt = """בחר מחשבון מתאים לאתר.

אתר:
=== כותרת ===
הלוואות ומשכנתאות - כלל ביטוח

=== תיאור ===
כלל מציעה הלוואות לכל מטרה

מחשבונים:
[{"id": 1, "name": "מחשבון הלוואה"}, {"id": 2, "name": "מחשבון משכנתא"}]

החזר JSON:
{"calc_id": 1, "match_score": 0.9, "reasoning": "הסבר קצר", "suggested_new_calc": null}"""

    print("Calling AI...")
    response = await ollama.generate(
        system_prompt="השב JSON בלבד",
        user_prompt=prompt,
        model="hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        temperature=0.3,
        max_tokens=400
    )
    
    print("=" * 60)
    print("RAW RESPONSE:")
    print(response)
    print("=" * 60)
    
    # Clean thinking tags
    cleaned = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    print("CLEANED:")
    print(cleaned[:500])
    
    # Try to find JSON
    start_idx = cleaned.find('{')
    if start_idx != -1:
        brace_count = 0
        for i, char in enumerate(cleaned[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    potential_json = cleaned[start_idx:i+1]
                    print("=" * 60)
                    print("EXTRACTED JSON:")
                    print(potential_json)
                    break

if __name__ == "__main__":
    asyncio.run(test())
