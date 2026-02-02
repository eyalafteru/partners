import sqlite3
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('SELECT domain, recommended_calc_reason FROM scan_queue WHERE recommended_calc_id IS NOT NULL')
for r in c.fetchall():
    print(f"Domain: {r[0]}")
    print(f"Reason: {r[1]}")
    print("-" * 50)
