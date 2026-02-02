import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Progress
c.execute('SELECT rescan_processed, rescan_total, rescan_status FROM scan_campaigns WHERE id=1')
row = c.fetchone()
print(f'סטטוס: {row[2]}')
print(f'התקדמות: {row[0]}/{row[1]}')

# Sites with content
c.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id=1 AND html_text IS NOT NULL AND length(html_text) > 100')
has_content = c.fetchone()[0]
print(f'אתרים עם תוכן: {has_content}')

# Sites with navigation
c.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id=1 AND nav_links IS NOT NULL AND nav_links != "[]"')
has_nav = c.fetchone()[0]
print(f'אתרים עם navigation: {has_nav}')

# Sites with meta
c.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id=1 AND meta_title IS NOT NULL AND length(meta_title) > 0')
has_meta = c.fetchone()[0]
print(f'אתרים עם meta: {has_meta}')

# Total
c.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id=1')
total = c.fetchone()[0]
print(f'סה"כ אתרים: {total}')

conn.close()
