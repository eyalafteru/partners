"""Test with wait between models"""
import httpx
import time

# Step 1: Summarize
print("STEP 1: Summarize with gemma2:9b")
with httpx.Client(timeout=60) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": "סכם: הלוואות ומשכנתאות כלל ביטוח",
        "stream": False,
        "options": {"num_predict": 50}
    })
    print(f"Summary: {response.json().get('response', '')[:100]}")

# Unload gemma2
print("Unloading gemma2...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b", "prompt": "", "keep_alive": "0"
    })

# WAIT for GPU to clear
print("Waiting 5 seconds for GPU to clear...")
time.sleep(5)

# Check GPU
with httpx.Client(timeout=10) as client:
    ps = client.get("http://localhost:11434/api/ps").json()
    print(f"GPU models: {[m['name'] for m in ps.get('models', [])]}")

# Step 2: Match
print("\nSTEP 2: Match with DictaLM")
with httpx.Client(timeout=120) as client:
    response = client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "בחר: [{\"id\": 6, \"name\": \"מחשבון ריבית\"}]. החזר: {\"calc_id\": 6}",
        "stream": False,
        "options": {"num_predict": 50}
    })
    print(f"Match: {response.json().get('response', 'EMPTY')}")

print("Done!")
