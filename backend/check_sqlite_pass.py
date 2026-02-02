"""בדיקת סיסמאות בSQLite הישן"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# רשימת טבלאות
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print("טבלאות:", tables)

# בדיקת api_keys
if 'api_keys' in tables:
    cursor.execute("SELECT * FROM api_keys")
    rows = cursor.fetchall()
    if rows:
        cursor.execute("PRAGMA table_info(api_keys)")
        cols = [c[1] for c in cursor.fetchall()]
        print("\napi_keys:")
        for row in rows:
            print(dict(zip(cols, row)))
    else:
        print("\napi_keys: ריק")

# בדיקת auto_reply_settings
if 'auto_reply_settings' in tables:
    cursor.execute("SELECT * FROM auto_reply_settings")
    rows = cursor.fetchall()
    if rows:
        cursor.execute("PRAGMA table_info(auto_reply_settings)")
        cols = [c[1] for c in cursor.fetchall()]
        print("\nauto_reply_settings:")
        for row in rows:
            print(dict(zip(cols, row)))
    else:
        print("\nauto_reply_settings: ריק")

# חיפוש טבלאות עם email/password
for table in tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [c[1] for c in cursor.fetchall()]
        if any('pass' in c.lower() or 'email' in c.lower() or 'imap' in c.lower() or 'smtp' in c.lower() for c in cols):
            print(f"\n{table} - עמודות מעניינות:", [c for c in cols if 'pass' in c.lower() or 'email' in c.lower() or 'imap' in c.lower() or 'smtp' in c.lower()])
    except:
        pass

conn.close()
