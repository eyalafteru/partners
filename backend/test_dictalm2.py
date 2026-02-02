"""Test DictaLM model - full response"""
import httpx
import json

prompt = """בחר מחשבון:
אתר: הלוואות ומשכנתאות
מחשבונים: [{"id": 6, "name": "מחשבון ריבית"}]
החזר JSON בפורמט הזה בדיוק:
{"calc_id": 6, "match_score": 0.9, "reasoning": "הלוואות"}"""

print("Testing DictaLM-24B...")
with httpx.Client(timeout=120) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": prompt,
        "system": "החזר JSON בלבד ללא הסברים",
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 150}
    })
    
    print(f"Status: {response.status_code}")
    print(f"Full response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
