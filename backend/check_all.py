import requests
import sqlite3

print("=== Campaign Status ===")
for i in [1,2,3,4,5]:
    try:
        r = requests.get(f'http://localhost:8000/api/scans/{i}/match-calculators/status', timeout=5)
        d = r.json()
        status = 'Running' if d.get('is_running') else 'Done'
        processed = d.get('processed', 0)
        total = d.get('total', 0)
        print(f"Campaign {i}: {status} ({processed}/{total})")
    except Exception as e:
        print(f"Campaign {i}: Error - {e}")

print("\n=== Database Stats ===")
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL')
print(f"Total matched: {c.fetchone()[0]}")
c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND LENGTH(html_text) > 100 AND recommended_calc_id IS NULL')
print(f"With content, not matched: {c.fetchone()[0]}")
