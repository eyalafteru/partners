"""
תהליך עבודה מלא - התאמת מחשבונים לכל הדומיינים
1. התאמה לדומיינים עם תוכן
2. סריקה מחדש לדומיינים בלי תוכן
3. התאמה לדומיינים שנסרקו מחדש
"""
import asyncio
import requests
import time
import sqlite3
from datetime import datetime

API_BASE = "http://localhost:8000"

def get_stats():
    """Get current stats"""
    conn = sqlite3.connect('partnercalc.db')
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM scan_queue')
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND LENGTH(html_text) > 100')
    with_content = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM scan_queue WHERE recommended_calc_id IS NOT NULL')
    matched = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND LENGTH(html_text) > 100 AND recommended_calc_id IS NULL')
    need_match = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NULL OR LENGTH(html_text) < 100')
    no_content = c.fetchone()[0]
    
    conn.close()
    
    return {
        'total': total,
        'with_content': with_content,
        'matched': matched,
        'need_match': need_match,
        'no_content': no_content
    }

def get_all_campaigns():
    """Get all campaign IDs"""
    conn = sqlite3.connect('partnercalc.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT id FROM scan_campaigns')
    campaigns = [row[0] for row in c.fetchall()]
    conn.close()
    return campaigns

def start_matching(campaign_id):
    """Start calculator matching for a campaign"""
    try:
        r = requests.post(f"{API_BASE}/api/scans/{campaign_id}/match-calculators", timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Error starting matching for campaign {campaign_id}: {e}")
        return False

def check_matching_status(campaign_id):
    """Check if matching is still running"""
    try:
        r = requests.get(f"{API_BASE}/api/scans/{campaign_id}/match-calculators/status", timeout=10)
        data = r.json()
        return data.get('is_running', False), data.get('processed', 0), data.get('total', 0)
    except:
        return False, 0, 0

def start_rescan(campaign_id):
    """Start rescan for a campaign"""
    try:
        r = requests.post(f"{API_BASE}/api/scans/{campaign_id}/rescan", timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Error starting rescan for campaign {campaign_id}: {e}")
        return False

def check_rescan_status(campaign_id):
    """Check if rescan is still running"""
    try:
        r = requests.get(f"{API_BASE}/api/scans/{campaign_id}", timeout=10)
        data = r.json()
        return data.get('rescan_status') == 'running'
    except:
        return False

def main():
    print("=" * 60)
    print("🚀 תהליך עבודה מלא - התאמת מחשבונים")
    print("=" * 60)
    
    # Initial stats
    stats = get_stats()
    print(f"\n📊 מצב התחלתי:")
    print(f"   סה\"כ דומיינים: {stats['total']}")
    print(f"   עם תוכן: {stats['with_content']}")
    print(f"   כבר הותאמו: {stats['matched']}")
    print(f"   צריכים התאמה: {stats['need_match']}")
    print(f"   בלי תוכן: {stats['no_content']}")
    
    campaigns = get_all_campaigns()
    print(f"\n📋 נמצאו {len(campaigns)} קמפיינים")
    
    # Phase 1: Match all domains with content
    if stats['need_match'] > 0:
        print(f"\n🧮 שלב 1: התאמת {stats['need_match']} דומיינים עם תוכן...")
        
        for campaign_id in campaigns:
            print(f"\n   ▶️ מתחיל התאמה לקמפיין {campaign_id}...")
            if start_matching(campaign_id):
                # Wait for completion
                while True:
                    time.sleep(5)
                    is_running, processed, total = check_matching_status(campaign_id)
                    if not is_running:
                        print(f"   ✅ קמפיין {campaign_id}: הסתיים ({processed}/{total})")
                        break
                    print(f"   ⏳ קמפיין {campaign_id}: {processed}/{total}...")
    
    # Check stats after matching
    stats = get_stats()
    print(f"\n📊 מצב אחרי התאמה:")
    print(f"   הותאמו: {stats['matched']}")
    print(f"   צריכים התאמה: {stats['need_match']}")
    
    # Phase 2: Rescan domains without content
    if stats['no_content'] > 0:
        print(f"\n🔄 שלב 2: סריקה מחדש ל-{stats['no_content']} דומיינים בלי תוכן...")
        
        for campaign_id in campaigns:
            print(f"\n   ▶️ מתחיל סריקה מחדש לקמפיין {campaign_id}...")
            if start_rescan(campaign_id):
                # Wait for completion (with timeout)
                timeout = 300  # 5 minutes max per campaign
                start_time = time.time()
                while time.time() - start_time < timeout:
                    time.sleep(10)
                    if not check_rescan_status(campaign_id):
                        print(f"   ✅ קמפיין {campaign_id}: סריקה הסתיימה")
                        break
                    print(f"   ⏳ קמפיין {campaign_id}: סורק...")
    
    # Phase 3: Match newly scanned domains
    stats = get_stats()
    if stats['need_match'] > 0:
        print(f"\n🧮 שלב 3: התאמה ל-{stats['need_match']} דומיינים חדשים...")
        
        for campaign_id in campaigns:
            print(f"\n   ▶️ מתחיל התאמה לקמפיין {campaign_id}...")
            if start_matching(campaign_id):
                while True:
                    time.sleep(5)
                    is_running, processed, total = check_matching_status(campaign_id)
                    if not is_running:
                        print(f"   ✅ קמפיין {campaign_id}: הסתיים ({processed}/{total})")
                        break
                    print(f"   ⏳ קמפיין {campaign_id}: {processed}/{total}...")
    
    # Final stats
    stats = get_stats()
    print("\n" + "=" * 60)
    print("🎉 תהליך הסתיים!")
    print("=" * 60)
    print(f"\n📊 מצב סופי:")
    print(f"   סה\"כ דומיינים: {stats['total']}")
    print(f"   עם תוכן: {stats['with_content']}")
    print(f"   הותאמו: {stats['matched']} ✅")
    print(f"   עדיין צריכים התאמה: {stats['need_match']}")
    print(f"   בלי תוכן: {stats['no_content']}")
    
    success_rate = (stats['matched'] / stats['total'] * 100) if stats['total'] > 0 else 0
    print(f"\n   📈 אחוז הצלחה: {success_rate:.1f}%")

if __name__ == "__main__":
    main()
