import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# Check if column exists
cursor.execute('PRAGMA table_info(calculators)')
columns = [col[1] for col in cursor.fetchall()]
print('Existing columns:', columns)

if 'category' not in columns:
    cursor.execute("ALTER TABLE calculators ADD COLUMN category VARCHAR(100) DEFAULT 'הלוואות ומימון'")
    conn.commit()
    print('✅ Added category column')
else:
    print('✅ Column already exists')

conn.close()
