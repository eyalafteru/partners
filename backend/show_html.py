import sqlite3
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT domain, html_text
    FROM scan_queue 
    WHERE domain='hani.co.il'
''')
r = c.fetchone()
if r:
    print(f"Domain: {r[0]}")
    print(f"HTML Text (first 1500 chars):")
    print("-" * 50)
    print(r[1][:1500] if r[1] else "EMPTY!")
