"""Check content without AI call"""
import sqlite3
import json

# Get avraha content
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT nav_links, meta_title, meta_description, html_text, business_type
    FROM scan_queue WHERE domain = 'avraha.com'
''')
r = c.fetchone()

if r:
    nav_links, meta_title, meta_description, html_text, business_type = r
    
    print(f"Domain: avraha.com")
    print(f"Business type: {business_type}")
    print(f"nav_links: {nav_links[:200] if nav_links else 'NONE'}")
    print(f"meta_title: {meta_title}")
    print(f"meta_description: {meta_description}")
    print(f"html_text length: {len(html_text) if html_text else 0}")
    print()
    
    # Build content like scans.py does
    content_parts = []
    
    if nav_links:
        try:
            nav_data = json.loads(nav_links)
            nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
            if nav_texts:
                content_parts.append(f"=== תפריט ===\n" + ", ".join(nav_texts[:20]))
        except Exception as e:
            print(f"nav_links parse error: {e}")
    
    if meta_title:
        content_parts.append(f"=== כותרת ===\n{meta_title}")
    if meta_description:
        content_parts.append(f"=== תיאור ===\n{meta_description}")
    if html_text:
        content_parts.append(f"=== תוכן ===\n{html_text[:1000]}")
    
    site_content = "\n\n".join(content_parts)[:3000]
    
    print(f"Total content length: {len(site_content)}")
    print("=" * 50)
    print("CONTENT:")
    print(site_content[:1500])
else:
    print("No data for avraha.com")
