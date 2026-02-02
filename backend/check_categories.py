import pymysql

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='partnercalc', 
    password='partnercalc123', 
    database='partnercalc'
)
cursor = conn.cursor()

# Check leads with category
cursor.execute("SELECT COUNT(*) FROM leads WHERE category IS NOT NULL AND category != ''")
with_cat = cursor.fetchone()[0]
print(f"Leads with category: {with_cat}")

# Check scan_queue with campaign and business_type
cursor.execute("""
    SELECT sq.domain, sq.business_type, sc.keywords, sc.name
    FROM scan_queue sq
    JOIN scan_campaigns sc ON sq.campaign_id = sc.id
    WHERE sq.business_type IS NOT NULL
    LIMIT 5
""")
print("\nScan Queue with campaign info:")
for row in cursor.fetchall():
    print(f"  {row[0]}: type={row[1]}, campaign={row[3]}")

# Check if we can link leads to scan_queue by domain
cursor.execute("""
    SELECT COUNT(*) 
    FROM leads l
    JOIN scan_queue sq ON l.domain = sq.domain
    WHERE sq.campaign_id IS NOT NULL
""")
linkable = cursor.fetchone()[0]
print(f"\nLeads that can be linked to campaigns via domain: {linkable}")

conn.close()
