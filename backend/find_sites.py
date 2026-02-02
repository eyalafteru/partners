import sqlite3
import sys

search = sys.argv[1] if len(sys.argv) > 1 else "מימון"

c = sqlite3.connect('partnercalc.db').cursor()

# Search by content or domain
query = f"%{search}%"
c.execute('''SELECT domain, recommended_calc_id, recommended_calc_score, 
             recommended_calc_reason, all_recommended_calcs, business_type
             FROM scan_queue 
             WHERE html_text LIKE ? OR domain LIKE ? OR meta_title LIKE ?
             LIMIT 10''', (query, query, query))

results = c.fetchall()
print(f"Found {len(results)} sites matching '{search}':\n")

for r in results:
    print(f"=== {r[0]} ===")
    print(f"  Business type: {r[5]}")
    print(f"  Calc ID: {r[1]}")
    print(f"  Score: {r[2]}")
    print(f"  Reason: {r[3][:80] if r[3] else 'None'}")
    print(f"  All calcs: {r[4][:100] if r[4] else 'None'}")
    print()
