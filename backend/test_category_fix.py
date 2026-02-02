"""Test the category variable fix"""
import pymysql
import json

conn = pymysql.connect(
    host='localhost', 
    port=3306, 
    user='partnercalc', 
    password='partnercalc123', 
    database='partnercalc'
)
cursor = conn.cursor()

# Get a sample lead
cursor.execute("SELECT id, domain, site_name FROM leads LIMIT 1")
lead = cursor.fetchone()
lead_id, domain, site_name = lead
print(f"Lead: {domain} (ID: {lead_id})")

# Try to find campaign via scan_queue (the new fallback logic)
cursor.execute("""
    SELECT sc.id, sc.name, sc.keywords
    FROM scan_campaigns sc
    JOIN scan_queue sq ON sq.campaign_id = sc.id
    WHERE sq.domain = %s
    LIMIT 1
""", (domain,))
result = cursor.fetchone()

if result:
    campaign_id, campaign_name, keywords_json = result
    print(f"Found campaign: {campaign_name}")
    
    # Parse keywords to get category
    try:
        keywords = json.loads(keywords_json) if isinstance(keywords_json, str) else keywords_json
        if keywords:
            category = keywords[0]
            print(f"Category (first keyword): {category}")
    except Exception as e:
        print(f"Error parsing keywords: {e}")
        category = campaign_name
        print(f"Fallback to campaign name: {category}")
else:
    print("No campaign found via scan_queue!")

# Test with template
template = "היי, הגעתי לאתר שלכם דרך חיפוש על {{category}}"
if result:
    rendered = template.replace("{{category}}", category)
    print(f"\n--- Template Test ---")
    print(f"Original: {template}")
    print(f"Rendered: {rendered}")

conn.close()
print("\n✅ Test completed!")
