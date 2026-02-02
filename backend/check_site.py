import sqlite3
import sys

domain = sys.argv[1] if len(sys.argv) > 1 else "check-box.co.il"

c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''SELECT domain, recommended_calc_id, recommended_calc_score, 
             recommended_calc_reason, all_recommended_calcs, 
             LENGTH(html_text) as content_len, business_type
             FROM scan_queue WHERE domain = ?''', (domain,))
r = c.fetchone()
if r:
    print(f"Domain: {r[0]}")
    print(f"Calc ID: {r[1]}")
    print(f"Score: {r[2]}")
    print(f"Reason: {r[3]}")
    print(f"All calcs JSON: {r[4]}")
    print(f"Content length: {r[5]}")
    print(f"Business type: {r[6]}")
else:
    print(f"Domain {domain} not found")
