"""Reset scanned sites for re-scraping to get html_text"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Check how many sites are missing html_text
c.execute("SELECT COUNT(*) FROM scan_queue WHERE status IN ('matched', 'discarded') AND (html_text IS NULL OR html_text = '')")
missing = c.fetchone()[0]

c.execute("SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND html_text != ''")
has_text = c.fetchone()[0]

print(f'Sites with html_text: {has_text}')
print(f'Sites missing html_text: {missing}')

# Reset status to pending for re-scraping
if missing > 0:
    c.execute("UPDATE scan_queue SET status = 'pending', html_text = NULL, html_body = NULL, business_type = NULL, ai_analyzed_at = NULL WHERE status IN ('matched', 'discarded') AND (html_text IS NULL OR html_text = '')")
    conn.commit()
    print(f'Reset {missing} sites to pending for re-scraping')

conn.close()
print('Done!')
