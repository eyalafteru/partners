"""Quick test - simpler prompt, faster model"""
import httpx

# Very simple prompt
prompt = """בחר מחשבון:
אתר: הלוואות ומשכנתאות
מחשבונים: [{"id": 6, "name": "מחשבון ריבית"}]
החזר: {"calc_id": 6, "match_score": 0.9, "reasoning": "הלוואות"}"""

print("Testing gemma2:9b (small & fast)...")
with httpx.Client(timeout=60) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": prompt,
        "system": "JSON only",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 100}
    })
    result = response.json()

print(f"Response: {result.get('response', 'EMPTY')}")
