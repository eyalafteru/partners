import requests
import json

r = requests.get('http://localhost:8000/api/scans/1/queue?page=0&status=matched', timeout=10)
data = r.json()

# Handle both list and dict responses
items = data.get('results', data) if isinstance(data, dict) else data

if items:
    for item in items[:3]:
        print(f"=== {item.get('domain') or item.get('url', 'unknown')} ===")
        print(f"  calc_id: {item.get('recommended_calc_id')}")
        print(f"  calc_name: {item.get('recommended_calc_name')}")
        calcs = item.get('all_recommended_calcs')
        if calcs:
            print(f"  all_recommended_calcs ({len(calcs)} items):")
            for c in calcs:
                print(f"    - {c.get('calc_name', 'ID:'+str(c.get('calc_id')))}: {c.get('score')}")
        else:
            print(f"  all_recommended_calcs: None")
        print()
else:
    print("No matched results")
