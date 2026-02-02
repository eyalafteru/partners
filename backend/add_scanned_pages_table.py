"""
יצירת טבלת scanned_pages והוספת שדות ל-scan_queue
"""
import sqlite3

db_path = "partnercalc.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create scanned_pages table
print("Creating scanned_pages table...")
cursor.execute("""
CREATE TABLE IF NOT EXISTS scanned_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_item_id INTEGER NOT NULL,
    url VARCHAR(500) NOT NULL,
    path VARCHAR(255),
    page_type VARCHAR(50),
    title VARCHAR(500),
    html_text TEXT,
    has_contact_form INTEGER DEFAULT 0,
    form_selector VARCHAR(255),
    form_html TEXT,
    status VARCHAR(20) DEFAULT 'scraped',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (queue_item_id) REFERENCES scan_queue(id)
)
""")
print("✅ Created scanned_pages table")

# Create index
cursor.execute("CREATE INDEX IF NOT EXISTS ix_scanned_pages_queue_item_id ON scanned_pages(queue_item_id)")
print("✅ Created index on queue_item_id")

# Add new columns to scan_queue
print("\nAdding new columns to scan_queue...")

cursor.execute("PRAGMA table_info(scan_queue)")
existing_columns = [row[1] for row in cursor.fetchall()]

new_columns = [
    ("deep_scan_status", "VARCHAR(20) DEFAULT 'pending'"),
    ("pages_scanned", "INTEGER DEFAULT 0"),
    ("deep_scan_at", "DATETIME"),
    ("recommended_calc_id", "INTEGER"),
    ("recommended_calc_score", "REAL"),
    ("recommended_calc_reason", "TEXT"),
    ("calc_matched_at", "DATETIME"),
]

for col_name, col_def in new_columns:
    if col_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE scan_queue ADD COLUMN {col_name} {col_def}")
            print(f"✅ Added column: {col_name}")
        except Exception as e:
            print(f"❌ Error adding {col_name}: {e}")
    else:
        print(f"⏭️ Column already exists: {col_name}")

conn.commit()
conn.close()

print("\n✅ Done!")
