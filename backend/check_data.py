import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

query = """
SELECT 
    domain, 
    LENGTH(nav_links) as nav_len,
    LENGTH(meta_title) as title_len,
    LENGTH(meta_description) as desc_len,
    LENGTH(html_text) as html_len,
    business_type
FROM scan_queue 
WHERE campaign_id=1 
AND business_type IN ('lead_site', 'small_business')
AND html_text IS NOT NULL
LIMIT 10
"""

c.execute(query)
rows = c.fetchall()

print(f"Found {len(rows)} items with content")
print("-" * 80)
for row in rows:
    domain, nav, title, desc, html, btype = row
    print(f"{domain}: nav={nav or 0}, title={title or 0}, desc={desc or 0}, html={html or 0}, type={btype}")
