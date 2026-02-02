"""Test full flow - summarize then match"""
import httpx
import json

# Step 1: Summarize with gemma2:9b
print("=" * 50)
print("STEP 1: Summarize with gemma2:9b")
print("=" * 50)

content = """הלוואות ומשכנתאות - כלל ביטוח ופיננסים
הדרך לרכישת בית החלומות שלכם לא חייבת לעבור בבנק.
כלל מציעה לכם גישה שונה למימון המשכנתא.
זקוקים להלוואה לרכישת דירה או הלוואה לכל מטרה?"""

with httpx.Client(timeout=60) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": f"סכם בקצרה: {content}",
        "system": "סכם בעברית ב-2 משפטים",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 100}
    })
    summary = response.json().get("response", "")
    print(f"Summary: {summary}")

# Step 2: Unload gemma2
print("\nUnloading gemma2:9b...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": "",
        "keep_alive": "0"
    })
print("Done")

# Check GPU
print("\nGPU Status:")
with httpx.Client(timeout=10) as client:
    ps = client.get("http://localhost:11434/api/ps").json()
    print(f"Loaded models: {[m['name'] for m in ps.get('models', [])]}")

# Step 3: Match with DictaLM
print("\n" + "=" * 50)
print("STEP 2: Match with DictaLM")
print("=" * 50)

prompt = f"""בחר מחשבון:
אתר: {summary[:200] if summary else content[:200]}
מחשבונים: [{{"id": 6, "name": "מחשבון ריבית"}}]
החזר JSON: {{"calc_id": 6, "match_score": 0.9, "reasoning": "הסבר"}}"""

with httpx.Client(timeout=120) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": prompt,
        "system": "החזר JSON בלבד",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 150}
    })
    result = response.json()
    match_response = result.get("response", "EMPTY")
    print(f"Match response: {match_response}")

# Step 4: Unload DictaLM
print("\nUnloading DictaLM...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "",
        "keep_alive": "0"
    })
print("Done!")
