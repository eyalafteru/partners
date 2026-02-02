import httpx
import json

try:
    response = httpx.get('http://localhost:8000/api/scans', timeout=10)
    data = response.json()
    for c in data:
        print(f"ID={c['id']}, name={c['name']}, calc_matched={c.get('calc_matched',0)}, gpt_calc_matched={c.get('gpt_calc_matched', 'N/A')}")
except Exception as e:
    print(f'Error: {e}')
