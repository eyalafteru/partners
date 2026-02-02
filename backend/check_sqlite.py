"""Check SQLite database contents"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("=" * 50)
print("SQLite Database Contents")
print("=" * 50)

total_rows = 0
for table in tables:
    table_name = table[0]
    if table_name.startswith('alembic') or table_name.startswith('sqlite'):
        continue
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    count = cursor.fetchone()[0]
    total_rows += count
    status = "✅" if count > 0 else "⬜"
    print(f"{status} {table_name}: {count} rows")

print("=" * 50)
print(f"Total rows: {total_rows}")

# Show sample data from tables with content
print("\n" + "=" * 50)
print("Sample Data from Non-Empty Tables:")
print("=" * 50)

for table in tables:
    table_name = table[0]
    if table_name.startswith('alembic') or table_name.startswith('sqlite'):
        continue
    cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"\n📋 {table_name} ({count} rows):")
        cursor.execute(f"SELECT * FROM [{table_name}] LIMIT 3")
        rows = cursor.fetchall()
        # Get column names
        cursor.execute(f"PRAGMA table_info([{table_name}])")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"   Columns: {columns[:5]}..." if len(columns) > 5 else f"   Columns: {columns}")
        for row in rows:
            print(f"   → {str(row)[:100]}...")

conn.close()
