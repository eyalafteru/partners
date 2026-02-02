import sqlite3
c = sqlite3.connect('partnercalc.db').cursor()

# Count all lead_site/small_business with html_text
c.execute('''
    SELECT COUNT(*) FROM scan_queue 
    WHERE business_type IN ('lead_site', 'small_business')
    AND html_text IS NOT NULL
''')
total = c.fetchone()[0]

# Count with quality data
c.execute('''
    SELECT COUNT(*) FROM scan_queue 
    WHERE business_type IN ('lead_site', 'small_business')
    AND html_text IS NOT NULL
    AND (nav_links IS NOT NULL OR meta_title IS NOT NULL OR meta_description IS NOT NULL)
''')
quality = c.fetchone()[0]

print(f"Total items with html_text: {total}")
print(f"Items with quality data (nav/meta): {quality}")
print(f"Items without quality data: {total - quality}")
