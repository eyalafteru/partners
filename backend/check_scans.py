import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT 
        id,
        name,
        status,
        total_urls,
        scanned_count
    FROM scan_campaigns
    ORDER BY created_at DESC
''')

scans = cursor.fetchall()
print('סטטוס סריקות:\n')
for scan in scans:
    scan_id = scan[0]
    
    # Count AI analyzed
    cursor.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id = ? AND ai_analyzed_at IS NOT NULL', (scan_id,))
    ai_count = cursor.fetchone()[0]
    
    # Count deep scanned
    cursor.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id = ? AND deep_scan_status = ?', (scan_id, 'completed'))
    deep_count = cursor.fetchone()[0]
    
    # Count matched calculators
    cursor.execute('SELECT COUNT(*) FROM scan_queue WHERE campaign_id = ? AND recommended_calc_id IS NOT NULL', (scan_id,))
    matched_count = cursor.fetchone()[0]
    
    print(f'ID: {scan[0]}')
    print(f'שם: {scan[1]}')
    print(f'סטטוס: {scan[2]}')
    print(f'סה"כ URLs: {scan[3]}')
    print(f'נסרקו: {scan[4]}')
    print(f'מנותחים AI: {ai_count}')
    print(f'סריקה מעמיקה: {deep_count}')
    print(f'מחשבונים מותאמים: {matched_count}')
    print('-' * 50)

conn.close()
