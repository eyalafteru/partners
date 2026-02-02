"""Check MariaDB database contents"""
import pymysql

conn = pymysql.connect(
    host='localhost',
    port=3306,
    user='partnercalc',
    password='partnercalc123',
    database='partnercalc',
    charset='utf8mb4'
)
cursor = conn.cursor()

# Get all tables
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()

print("=" * 50)
print("MariaDB Database Contents")
print("=" * 50)

total_rows = 0
for table in tables:
    table_name = table[0]
    if table_name.startswith('alembic'):
        continue
    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
    count = cursor.fetchone()[0]
    total_rows += count
    status = "✅" if count > 0 else "⬜"
    print(f"{status} {table_name}: {count} rows")

print("=" * 50)
print(f"Total rows: {total_rows}")

conn.close()
