"""Test sequence with full response"""
import httpx
import json
import time

# Unload everything first
print("Unloading all models...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={"model": "gemma2:9b", "prompt": "", "keep_alive": "0"})
    client.post("http://localhost:11434/api/generate", json={"model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M", "prompt": "", "keep_alive": "0"})

time.sleep(3)

# Step 1: gemma2
print("\n1. Running gemma2:9b...")
with httpx.Client(timeout=60) as client:
    r = client.post("http://localhost:11434/api/generate", json={
        "model": "gemma2:9b",
        "prompt": "אמור שלום",
        "stream": False,
        "options": {"num_predict": 10}
    })
    print(f"gemma2 response: {r.json().get('response', '')}")

# Unload
print("\nUnloading gemma2...")
with httpx.Client(timeout=30) as client:
    client.post("http://localhost:11434/api/generate", json={"model": "gemma2:9b", "prompt": "", "keep_alive": "0"})

time.sleep(5)
print("Waiting 5s...")

# Step 2: DictaLM
print("\n2. Running DictaLM...")
with httpx.Client(timeout=180) as client:  # 3 minute timeout
    r = client.post("http://localhost:11434/api/generate", json={
        "model": "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        "prompt": "אמור שלום",
        "stream": False,
        "options": {"num_predict": 10}
    })
    data = r.json()
    print(f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)[:500]}")
    print(f"\nresponse field: '{data.get('response', 'EMPTY')}'")
