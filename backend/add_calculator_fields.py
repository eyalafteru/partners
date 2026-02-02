"""
הוספת שדות חדשים לטבלת calculators
"""
import sqlite3

db_path = "partnercalc.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check existing columns
cursor.execute("PRAGMA table_info(calculators)")
existing_columns = [row[1] for row in cursor.fetchall()]
print(f"Existing columns: {existing_columns}")

# Add new columns if they don't exist
new_columns = [
    ("ai_summary", "TEXT"),
    ("scraped_content", "TEXT"),
    ("scraped_at", "DATETIME"),
]

for col_name, col_type in new_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE calculators ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added column: {col_name}")
        except Exception as e:
            print(f"❌ Error adding {col_name}: {e}")
    else:
        print(f"⏭️ Column already exists: {col_name}")

conn.commit()
conn.close()

print("\n✅ Done!")
