"""
Migration script to add email system tables and columns
"""
import sqlite3

def migrate():
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    
    # ========== Create email_templates table ==========
    print("Creating email_templates table...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            body_text TEXT NOT NULL,
            body_html TEXT,
            category VARCHAR(50) DEFAULT 'first_contact',
            is_active BOOLEAN DEFAULT 1,
            variables TEXT DEFAULT '[]',
            usage_count INTEGER DEFAULT 0,
            total_opens INTEGER DEFAULT 0,
            total_clicks INTEGER DEFAULT 0,
            open_rate REAL DEFAULT 0.0,
            click_rate REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    print("✅ email_templates table created")
    
    # ========== Add columns to communication table ==========
    columns_to_add = [
        ("template_id", "INTEGER"),
        ("opens_count", "INTEGER DEFAULT 0"),
        ("clicks", "TEXT DEFAULT '[]'"),
        ("thread_id", "VARCHAR(100)"),
        ("in_reply_to_id", "INTEGER"),
    ]
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(communication)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            print(f"Adding column {col_name} to communication...")
            cursor.execute(f'ALTER TABLE communication ADD COLUMN {col_name} {col_type}')
            print(f"✅ Added {col_name}")
        else:
            print(f"⏭️ Column {col_name} already exists")
    
    # ========== Update auto_reply_settings table ==========
    auto_reply_columns = [
        ("default_template_id", "INTEGER"),
        ("ai_prompt_override", "TEXT"),
    ]
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auto_reply_settings'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(auto_reply_settings)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        for col_name, col_type in auto_reply_columns:
            if col_name not in existing_columns:
                print(f"Adding column {col_name} to auto_reply_settings...")
                cursor.execute(f'ALTER TABLE auto_reply_settings ADD COLUMN {col_name} {col_type}')
                print(f"✅ Added {col_name}")
            else:
                print(f"⏭️ Column {col_name} already exists")
    else:
        print("⚠️ auto_reply_settings table does not exist yet")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
