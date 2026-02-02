import sqlite3
import json

c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''SELECT domain, all_recommended_calcs, recommended_calc_reason, 
             recommended_calc_id, recommended_calc_score 
             FROM scan_queue WHERE recommended_calc_id IS NOT NULL''')

for r in c.fetchall():
    print(f'=== {r[0]} ===')
    if r[1]:
        # New format - multiple calculators
        calcs = json.loads(r[1])
        print('מחשבונים מומלצים:')
        for m in calcs:
            calc_id = m.get("calc_id")
            score = m.get("score")
            reason = m.get("reason", "")[:60]
            print(f'  - ID {calc_id}: {score} - {reason}')
    else:
        # Old format - single calculator
        print(f'מחשבון מומלץ: ID {r[3]} (ציון: {r[4]})')
        if r[2]:
            print(f'סיבה: {r[2][:80]}')
    print()
