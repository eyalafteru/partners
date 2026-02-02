"""
הוספת שדות navigation ומטא לטבלת scan_queue
"""
import sqlite3

def add_navigation_fields():
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(scan_queue)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    columns_to_add = [
        ("nav_links", "TEXT"),  # JSON as TEXT in SQLite
        ("meta_title", "TEXT"),
        ("meta_description", "TEXT"),
        ("meta_keywords", "TEXT"),
        ("has_menu_calculator", "INTEGER DEFAULT 0"),
    ]
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE scan_queue ADD COLUMN {col_name} {col_type}")
                print(f"✅ הוספה: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ {col_name}: {e}")
        else:
            print(f"✔️ קיים: {col_name}")
    
    conn.commit()
    conn.close()
    print("\n✅ Migration הושלם!")

if __name__ == "__main__":
    add_navigation_fields()
