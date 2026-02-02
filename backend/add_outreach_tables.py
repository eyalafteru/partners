"""
Add outreach tables and columns
הוספת טבלאות ועמודות ל-outreach system
"""
import sqlite3

def run_migration():
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    
    # Add new columns to leads table
    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN last_response_at DATETIME")
        print("✅ Added last_response_at to leads")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("⚠️ last_response_at already exists")
        else:
            print(f"❌ Error: {e}")
    
    try:
        cursor.execute("ALTER TABLE leads ADD COLUMN outreach_count INTEGER DEFAULT 0")
        print("✅ Added outreach_count to leads")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("⚠️ outreach_count already exists")
        else:
            print(f"❌ Error: {e}")
    
    # Create email_queue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER NOT NULL,
            template_id INTEGER,
            to_email VARCHAR(255) NOT NULL,
            subject VARCHAR(500) NOT NULL,
            body TEXT NOT NULL,
            scheduled_at DATETIME NOT NULL,
            sent_at DATETIME,
            status VARCHAR(50) DEFAULT 'pending',
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME,
            FOREIGN KEY (lead_id) REFERENCES leads(id),
            FOREIGN KEY (template_id) REFERENCES email_templates(id)
        )
    """)
    print("✅ Created email_queue table")
    
    # Create indexes for email_queue
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_lead_id ON email_queue(lead_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_status ON email_queue(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_queue_scheduled_at ON email_queue(scheduled_at)")
    print("✅ Created email_queue indexes")
    
    # Create blacklist table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) UNIQUE,
            domain VARCHAR(255),
            reason VARCHAR(100) NOT NULL,
            notes TEXT,
            source VARCHAR(100) DEFAULT 'manual',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created blacklist table")
    
    # Create indexes for blacklist
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_email ON blacklist(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_domain ON blacklist(domain)")
    print("✅ Created blacklist indexes")
    
    # Create outreach_settings table (for daily limit, timing, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS outreach_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key VARCHAR(100) UNIQUE NOT NULL,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✅ Created outreach_settings table")
    
    # Insert default settings
    default_settings = [
        ('daily_limit', '100'),
        ('start_hour', '8'),
        ('end_hour', '20'),
        ('interval_minutes', '15'),
        ('enabled', 'true'),
    ]
    
    for key, value in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO outreach_settings (key, value) VALUES (?, ?)
        """, (key, value))
    print("✅ Inserted default outreach settings")
    
    conn.commit()
    conn.close()
    
    print("\n🎉 Migration completed successfully!")

if __name__ == "__main__":
    run_migration()
