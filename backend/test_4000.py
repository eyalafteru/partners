"""Test with 4000 tokens after gemma2"""
import httpx
import time

# Unload all
print("Unloading all...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={"model": "gemma2:9b", "prompt": "", "keep_alive": "0"})
    client.post("http://localhost:11434/api/generate", json={"model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M", "prompt": "", "keep_alive": "0"})

time.sleep(2)

# Run gemma2
print("\n1. Running gemma2...")
with httpx.Client(timeout=60) as client:
    r = client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": "סכם: הלוואות ומשכנתאות",
        "stream": False,
        "options": {"num_predict": 100}
    })
    print(f"gemma2: {r.json().get('response', '')[:100]}")

# Unload
print("\nUnloading gemma2...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={"model": "gemma2:9b", "prompt": "", "keep_alive": "0"})

time.sleep(3)

# Run DictaLM with 4000 tokens
print("\n2. Running DictaLM with 4000 tokens...")
with httpx.Client(timeout=300) as client:
    r = client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "בחר: [{\"id\":6,\"name\":\"מחשבון ריבית\"}]. החזר JSON: {\"calc_id\":6,\"match_score\":0.9,\"reasoning\":\"הסבר\"}",
        "system": "JSON בלבד",
        "stream": False,
        "options": {"num_predict": 4000}
    })
    data = r.json()
    print(f"response: {data.get('response', 'EMPTY')}")
    print(f"done_reason: {data.get('done_reason', '?')}")

print("\nDone!")
