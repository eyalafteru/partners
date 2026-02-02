"""Check AI analysis results"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
c = conn.cursor()

# Check AI analyzed
c.execute('SELECT domain, business_type, business_type_reason FROM scan_queue WHERE business_type IS NOT NULL LIMIT 10')
results = c.fetchall()

print('=== Analyzed domains ===')
for r in results:
    reason = r[2][:50] if r[2] else ''
    print(f'{r[0]}: {r[1]} - {reason}')

c.execute('SELECT COUNT(*) FROM scan_queue WHERE business_type IS NOT NULL')
print(f'\nTotal analyzed: {c.fetchone()[0]}')

c.execute('SELECT COUNT(*) FROM scan_queue WHERE html_text IS NOT NULL AND LENGTH(html_text) > 100')
print(f'Total with html_text: {c.fetchone()[0]}')

conn.close()
