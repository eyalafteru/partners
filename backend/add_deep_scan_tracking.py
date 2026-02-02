"""
הוספת שדות tracking לסריקה מעמיקה והתאמת מחשבונים ב-ScanCampaign
"""
import sqlite3

def add_deep_scan_tracking_columns():
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(scan_campaigns)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = [
        ("deep_scan_status", "TEXT DEFAULT 'pending'"),
        ("deep_scan_processed", "INTEGER DEFAULT 0"),
        ("deep_scan_total", "INTEGER DEFAULT 0"),
        ("deep_scan_current", "TEXT"),
        ("calc_match_status", "TEXT DEFAULT 'pending'"),
        ("calc_match_processed", "INTEGER DEFAULT 0"),
        ("calc_match_total", "INTEGER DEFAULT 0"),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE scan_campaigns ADD COLUMN {col_name} {col_type}")
                print(f"✅ הוספה: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ {col_name}: {e}")
        else:
            print(f"✔️ קיים: {col_name}")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration הושלם!")

if __name__ == "__main__":
    add_deep_scan_tracking_columns()
