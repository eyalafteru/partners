"""Add suggested_new_calc column to scan_queue"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Check if column exists
c.execute("PRAGMA table_info(scan_queue)")
columns = [col[1] for col in c.fetchall()]

if 'suggested_new_calc' not in columns:
    c.execute("ALTER TABLE scan_queue ADD COLUMN suggested_new_calc TEXT")
    conn.commit()
    print("✅ Added suggested_new_calc column")
else:
    print("Column already exists")

conn.close()
