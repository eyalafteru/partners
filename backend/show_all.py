import sqlite3
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT domain, recommended_calc_id, recommended_calc_score, 
           substr(recommended_calc_reason,1,60), 
           substr(suggested_new_calc,1,80) 
    FROM scan_queue 
    WHERE recommended_calc_id IS NOT NULL OR suggested_new_calc IS NOT NULL
''')
for r in c.fetchall():
    print(f"Domain: {r[0]}")
    print(f"  Calc ID: {r[1]}, Score: {r[2]}")
    print(f"  Reason: {r[3]}")
    if r[4]:
        print(f"  💡 Suggestion: {r[4]}")
    print("-" * 50)
