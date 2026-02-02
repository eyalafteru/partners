import sqlite3
import json

c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT domain, nav_links, meta_title, meta_description, html_text
    FROM scan_queue 
    WHERE domain = 'clalbit.co.il'
''')
r = c.fetchone()

if r:
    domain, nav_links, meta_title, meta_description, html_text = r
    
    print(f"=== {domain} ===")
    print()
    
    # Build content like in scans.py
    content_parts = []
    
    if nav_links:
        try:
            nav_data = json.loads(nav_links)
            nav_texts = [link.get("text", "") for link in nav_data if link.get("text")]
            if nav_texts:
                content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
                print(f"✅ Nav: {len(nav_texts)} items")
        except:
            print(f"❌ Nav parse error")
    else:
        print("❌ No nav_links")
    
    if meta_title:
        content_parts.append(f"=== כותרת ===\n{meta_title}")
        print(f"✅ Title: {meta_title}")
    else:
        print("❌ No meta_title")
    
    if meta_description:
        content_parts.append(f"=== תיאור ===\n{meta_description}")
        print(f"✅ Desc: {meta_description[:50]}...")
    else:
        print("❌ No meta_description")
    
    if html_text:
        content_parts.append(f"=== תוכן העמוד ===\n{html_text[:3000]}")
        print(f"✅ HTML: {len(html_text)} chars")
    else:
        print("❌ No html_text")
    
    print()
    print("=" * 60)
    print("FINAL CONTENT SENT TO AI:")
    print("=" * 60)
    site_content = "\n\n".join(content_parts)[:6000]
    print(site_content[:2000])
