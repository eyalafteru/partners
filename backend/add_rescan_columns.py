"""
הוספת שדות rescan לטבלת scan_campaigns
"""
import sqlite3

db_path = "partnercalc.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(scan_campaigns)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing columns in scan_campaigns: {existing_columns}")

# Add new columns if they don't exist
new_columns = [
    ("rescan_status", "VARCHAR(20)"),
    ("rescan_processed", "INTEGER DEFAULT 0"),
    ("rescan_total", "INTEGER DEFAULT 0"),
]

for col_name, col_def in new_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE scan_campaigns ADD COLUMN {col_name} {col_def}")
            print(f"✅ Added column: {col_name}")
        except Exception as e:
            print(f"❌ Error adding {col_name}: {e}")
    else:
        print(f"⏭️ Column already exists: {col_name}")

conn.commit()
conn.close()

print("\n✅ Done!")
