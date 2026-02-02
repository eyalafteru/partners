"""Show exact prompt being sent to AI"""
import sqlite3
import json

# Get first site with content
c = sqlite3.connect('partnercalc.db').cursor()
c.execute('''
    SELECT domain, nav_links, meta_title, meta_description, html_text, business_type
    FROM scan_queue 
    WHERE html_text IS NOT NULL 
    AND business_type IN ('lead_site', 'small_business')
    LIMIT 1
''')
r = c.fetchone()

if not r:
    print("No sites with content found")
    exit()

domain, nav_links, meta_title, meta_description, html_text, business_type = r

# Build content like scans.py does
content_parts = []

if nav_links:
    try:
        nav_data = json.loads(nav_links)
        nav_texts = [link.get("text", "") for link in nav_data if isinstance(link, dict) and link.get("text")]
        if nav_texts:
            content_parts.append(f"=== תפריט ראשי ===\n" + ", ".join(nav_texts[:20]))
    except:
        pass

if meta_title:
    content_parts.append(f"=== כותרת ===\n{meta_title}")
if meta_description:
    content_parts.append(f"=== תיאור ===\n{meta_description}")
if html_text:
    content_parts.append(f"=== תוכן העמוד ===\n{html_text[:3000]}")

site_content = "\n\n".join(content_parts)[:6000]

# Get calculators
c.execute('SELECT id, name, ai_summary FROM calculators WHERE is_active = 1 LIMIT 10')
calcs = c.fetchall()
calcs_json = json.dumps([{"id": id, "name": name, "desc": (summary or "")[:100]} for id, name, summary in calcs], ensure_ascii=False)

# Build prompt like calculator_matcher.py does
MATCH_PROMPT = """בחר מחשבון מתאים לאתר.

אתר:
{site_content}

מחשבונים זמינים:
{calculators_json}

החזר JSON בלבד:
{{"calc_id": 1, "match_score": 0.9, "reasoning": "הסבר קצר", "suggested_new_calc": null}}

אם אין מחשבון מתאים, suggested_new_calc יכיל הצעה למחשבון חדש לפיתוח."""

# Check if content is too long - would trigger summarization
MAX_CONTENT_FOR_DIRECT_MATCH = 1500

print(f"=== DOMAIN: {domain} ===")
print(f"Content length: {len(site_content)} chars")
print(f"Would summarize: {len(site_content) > MAX_CONTENT_FOR_DIRECT_MATCH}")
print()

if len(site_content) > MAX_CONTENT_FOR_DIRECT_MATCH:
    # Simulate summarization - take first 500 chars
    processed_content = site_content[:500] + "..."
    print(">>> AFTER SUMMARIZATION (simulated):")
else:
    processed_content = site_content
    
prompt = MATCH_PROMPT.format(
    site_content=processed_content,
    calculators_json=calcs_json
)

print("=" * 60)
print("FULL PROMPT TO AI:")
print("=" * 60)
print(prompt)
print("=" * 60)
print(f"Total prompt length: {len(prompt)} chars")
