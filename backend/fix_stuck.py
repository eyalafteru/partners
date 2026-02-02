import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Reset stuck scan to failed
c.execute("UPDATE scan_campaigns SET status='failed', total_urls=0, scanned_count=0 WHERE id=2")
conn.commit()

# Check status
c.execute("SELECT id, name, status FROM scan_campaigns WHERE id=2")
print("Updated:", c.fetchone())

conn.close()
