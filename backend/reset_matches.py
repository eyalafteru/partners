import sqlite3
conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Reset all matches
c.execute('''
    UPDATE scan_queue 
    SET recommended_calc_id = NULL,
        recommended_calc_score = NULL,
        recommended_calc_reason = NULL,
        calc_matched_at = NULL
    WHERE recommended_calc_id IS NOT NULL
''')

rows = c.rowcount
conn.commit()
print(f"Reset {rows} matches")
