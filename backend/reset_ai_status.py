import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# Reset AI status for all stuck scans
cursor.execute("UPDATE scan_campaigns SET ai_current_domain = NULL")
rows = cursor.rowcount
conn.commit()
print(f'Reset {rows} scans AI status')

# Show current status
cursor.execute('SELECT id, name, status, ai_current_domain, ai_processed, ai_total FROM scan_campaigns')
for row in cursor.fetchall():
    name = row[1][:25] if row[1] else 'N/A'
    print(f'  Scan {row[0]}: {name} - Status: {row[2]}, AI: {row[3]} ({row[4]}/{row[5]})')

conn.close()
