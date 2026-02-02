import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Reset all AI classifications
c.execute('UPDATE scan_queue SET business_type = NULL, business_type_reason = NULL, ai_analyzed_at = NULL')
rows = c.rowcount

conn.commit()
conn.close()

print(f'Reset {rows} rows')
