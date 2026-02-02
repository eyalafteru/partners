import sqlite3
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT domain, 
           length(nav_links) as nav, 
           length(meta_title) as title,
           length(html_text) as html
    FROM scan_queue 
    WHERE business_type='lead_site' 
    LIMIT 5
''')
for r in c.fetchall():
    print(f"{r[0]}: nav={r[1] or 0}, title={r[2] or 0}, html={r[3] or 0}")
