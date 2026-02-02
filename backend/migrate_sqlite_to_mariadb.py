"""
Migrate data from SQLite to MariaDB
Maintains backward compatibility - SQLite file is preserved
"""
import sqlite3
import pymysql
from datetime import datetime

print("=" * 60)
print("🔄 SQLite → MariaDB Migration (v2 - Robust)")
print("=" * 60)

def get_mariadb_connection():
    """Create a new MariaDB connection"""
    return pymysql.connect(
        host='localhost',
        port=3306,
        user='partnercalc',
        password='partnercalc123',
        database='partnercalc',
        charset='utf8mb4',
        autocommit=True,
        max_allowed_packet=64*1024*1024,  # 64MB
        read_timeout=300,
        write_timeout=300
    )

# Connect to SQLite
sqlite_conn = sqlite3.connect('partnercalc.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Connect to MariaDB
mariadb_conn = get_mariadb_connection()
mariadb_cursor = mariadb_conn.cursor()

# Step 1: Create missing outreach_settings table
print("\n📋 Step 1: Creating missing table 'outreach_settings'...")
mariadb_cursor.execute("""
    CREATE TABLE IF NOT EXISTS outreach_settings (
        id INT AUTO_INCREMENT PRIMARY KEY,
        `key` VARCHAR(100) NOT NULL UNIQUE,
        `value` TEXT,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
""")
print("   ✅ Table created")

# Step 2: Disable foreign key checks for migration
print("\n🔓 Step 2: Disabling foreign key checks...")
mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
mariadb_cursor.execute("SET SESSION wait_timeout = 28800")
print("   ✅ Settings configured")

# Tables in order (parents before children)
tables_order = [
    'calculators',
    'scan_campaigns', 
    'prompts',
    'api_keys',
    'auto_reply_settings',
    'auto_reply_settings_legacy',
    'email_templates',
    'reply_scenarios',
    'outreach_settings',
    'leads',
    'scan_queue',
    'scanned_pages',
    'communication',
    'pending_replies',
    'installations',
    'ai_logs',
    'email_queue',
    'blacklist',
]

# Step 3: Migrate each table
print("\n📦 Step 3: Migrating data...")
total_migrated = 0
errors = []
BATCH_SIZE = 50  # Insert 50 rows at a time

for table_name in tables_order:
    try:
        # Check if table exists in SQLite
        sqlite_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not sqlite_cursor.fetchone():
            print(f"   ⏭️  {table_name}: Not in SQLite, skipping")
            continue
        
        # Get row count
        sqlite_cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        row_count = sqlite_cursor.fetchone()[0]
        
        if row_count == 0:
            print(f"   ⬜ {table_name}: 0 rows (empty)")
            continue
        
        # Get column names
        sqlite_cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in sqlite_cursor.fetchall()]
        
        # Clear existing data in MariaDB (if any)
        try:
            mariadb_cursor.execute(f"DELETE FROM `{table_name}`")
        except:
            pass  # Table might not exist in MariaDB
        
        # Prepare insert statement
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join([f'`{col}`' for col in columns])
        insert_sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
        
        # Get data from SQLite in batches
        sqlite_cursor.execute(f"SELECT * FROM [{table_name}]")
        
        inserted = 0
        batch_errors = 0
        
        while True:
            rows = sqlite_cursor.fetchmany(BATCH_SIZE)
            if not rows:
                break
            
            for row in rows:
                try:
                    # Convert Row to tuple
                    values = tuple(row)
                    mariadb_cursor.execute(insert_sql, values)
                    inserted += 1
                except pymysql.err.InterfaceError:
                    # Reconnect and retry
                    mariadb_conn = get_mariadb_connection()
                    mariadb_cursor = mariadb_conn.cursor()
                    mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                    try:
                        mariadb_cursor.execute(insert_sql, values)
                        inserted += 1
                    except Exception as e2:
                        batch_errors += 1
                except Exception as row_error:
                    batch_errors += 1
                    if batch_errors <= 3:
                        errors.append(f"{table_name}: {str(row_error)[:60]}")
        
        total_migrated += inserted
        status = "✅" if batch_errors == 0 else "⚠️"
        error_info = f" ({batch_errors} errors)" if batch_errors > 0 else ""
        print(f"   {status} {table_name}: {inserted}/{row_count} rows migrated{error_info}")
        
    except Exception as e:
        errors.append(f"{table_name}: {str(e)[:80]}")
        print(f"   ❌ {table_name}: Error - {str(e)[:50]}")

# Step 4: Re-enable foreign key checks
print("\n🔒 Step 4: Re-enabling foreign key checks...")
try:
    mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("   ✅ FK checks enabled")
except:
    mariadb_conn = get_mariadb_connection()
    mariadb_cursor = mariadb_conn.cursor()
    mariadb_cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    print("   ✅ FK checks enabled (reconnected)")

# Step 5: Verify migration
print("\n🔍 Step 5: Verifying migration...")
mariadb_cursor.execute("SHOW TABLES")
tables = mariadb_cursor.fetchall()

verification_total = 0
for table in tables:
    table_name = table[0]
    mariadb_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = mariadb_cursor.fetchone()[0]
    verification_total += count
    if count > 0:
        print(f"   ✅ {table_name}: {count} rows")

# Summary
print("\n" + "=" * 60)
print("📊 MIGRATION SUMMARY")
print("=" * 60)
print(f"   Total rows migrated: {total_migrated}")
print(f"   Total rows in MariaDB: {verification_total}")
print(f"   Errors: {len(errors)}")

if errors:
    print("\n⚠️  Errors encountered:")
    for err in errors[:10]:
        print(f"   • {err}")
    if len(errors) > 10:
        print(f"   ... and {len(errors) - 10} more")

print("\n" + "=" * 60)
if verification_total > 0:
    print("✅ MIGRATION COMPLETED!")
    print("   SQLite file preserved as backup: partnercalc.db")
    print("   MariaDB is now the active database")
else:
    print("❌ MIGRATION FAILED - Check errors above")
print("=" * 60)

# Close connections
sqlite_conn.close()
try:
    mariadb_conn.close()
except:
    pass
