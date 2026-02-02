"""Test AI response with the exact prompt"""
import httpx
import json
import re

prompt = """בחר מחשבון מתאים לאתר.

אתר:
=== כותרת ===
הלוואות ומשכנתאות - כלל ביטוח ופיננסים

=== תיאור ===
הדרך לרכישת בית החלומות שלכם לא חייבת לעבור בבנק.

מחשבונים זמינים:
[{"id": 6, "name": "מחשבון ריבית אפקטיבית"}, {"id": 7, "name": "מחשבון קיצור הלוואה"}, {"id": 8, "name": "מחשבון עמלת פירעון מוקדם"}, {"id": 9, "name": "מחשבון הלוואת בלון"}]

החזר JSON בלבד:
{"calc_id": 6, "match_score": 0.9, "reasoning": "הסבר קצר", "suggested_new_calc": null}"""

payload = {
    "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
    "prompt": prompt,
    "system": "השב JSON בלבד. ללא הסברים.",
    "stream": False,
    "options": {"temperature": 0.2, "num_predict": 300}
}

print("Calling AI...")
with httpx.Client(timeout=120) as client:
    response = client.post("http://localhost:11434/api/generate", json=payload)
    result = response.json()

raw = result.get("response", "")
print(f"\n=== RAW RESPONSE ({len(raw)} chars) ===")
print(raw)
print()

# Try to parse like calculator_matcher does
response = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
response = re.sub(r'<\|.*?\|>', '', response)

# Find JSON
start_idx = response.find('{')
if start_idx >= 0:
    brace_count = 0
    for i, char in enumerate(response[start_idx:], start_idx):
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                json_str = response[start_idx:i+1]
                print(f"=== EXTRACTED JSON ===")
                print(json_str)
                try:
                    parsed = json.loads(json_str)
                    print(f"\n=== PARSED ===")
                    print(json.dumps(parsed, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(f"Parse error: {e}")
                break
else:
    print("No JSON found!")

# Unload model
print("\nUnloading model...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "",
        "keep_alive": "0"
    })
print("Done!")
