import httpx
import json

response = httpx.get("http://localhost:8001/api/scans/")
data = response.json()

print("Response from /api/scans/:\n")
for scan in data:
    print(f"\n=== {scan['name']} ===")
    print(f"ID: {scan['id']}")
    print(f"Status: {scan['status']}")
    print(f"AI Analyzed: {scan.get('ai_analyzed', 'MISSING!')}")
    print(f"Deep Scanned: {scan.get('deep_scanned', 'MISSING!')}")
    print(f"Calc Matched: {scan.get('calc_matched', 'MISSING!')}")
