import sqlite3
import sys

scan_id = int(sys.argv[1]) if len(sys.argv) > 1 else 2

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# Get current status
cursor.execute('SELECT id, name, status, total_urls FROM scan_campaigns WHERE id = ?', (scan_id,))
row = cursor.fetchone()
if row:
    print(f"Scan {row[0]}: {row[1]} - Status: {row[2]}, URLs: {row[3]}")
    
    # Reset to failed so we can retry
    cursor.execute('UPDATE scan_campaigns SET status = ? WHERE id = ?', ('failed', scan_id))
    conn.commit()
    print(f"✅ Reset scan {scan_id} to 'failed' - now you can retry it")
else:
    print(f"Scan {scan_id} not found")

conn.close()
