import requests
import time
import sqlite3

def get_matched_count():
    conn = sqlite3.connect('partnercalc.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL')
    count = c.fetchone()[0]
    conn.close()
    return count

print("📊 מעקב אחרי התאמת מחשבונים...")
print("=" * 50)

while True:
    total_running = 0
    
    for campaign_id in [1, 2, 3, 4, 5]:
        try:
            r = requests.get(f'http://localhost:8000/api/scans/{campaign_id}/match-calculators/status', timeout=5)
            data = r.json()
            if data.get('is_running'):
                total_running += 1
                processed = data.get('processed', 0)
                total = data.get('total', 0)
                current = data.get('current_site', '')
                print(f"  קמפיין {campaign_id}: {processed}/{total} - {current}")
        except Exception as e:
            pass
    
    matched = get_matched_count()
    print(f"🧮 הותאמו עד כה: {matched}")
    
    if total_running == 0:
        print("\n✅ כל ההתאמות הסתיימו!")
        break
    
    print(f"⏳ רצים: {total_running} קמפיינים")
    print("-" * 50)
    time.sleep(15)

# Final stats
print("\n📊 סטטיסטיקה סופית:")
conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL')
print(f"   הותאמו: {c.fetchone()[0]}")
c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND LENGTH(html_text) > 100 AND recommended_calc_id IS NULL')
print(f"   עדיין צריכים: {c.fetchone()[0]}")
conn.close()
