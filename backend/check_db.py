import sqlite3
from collections import Counter
from urllib.parse import urlparse

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# List tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

# Check scan_queue table
try:
    cursor.execute('SELECT url FROM scan_queue')
    urls = cursor.fetchall()
    
    # Extract domains
    domains = []
    for (url,) in urls:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            domains.append(domain)
        except:
            pass
    
    # Count duplicates
    counts = Counter(domains)
    duplicates = [(d, c) for d, c in counts.items() if c > 1]
    
    print(f'Total URLs: {len(urls)}')
    print(f'Unique domains: {len(counts)}')
    print(f'Domains with duplicates: {len(duplicates)}')
    if duplicates[:5]:
        print('Top duplicates:')
        for d, c in sorted(duplicates, key=lambda x: -x[1])[:5]:
            print(f'  {d}: {c}')
except Exception as e:
    print(f'Error: {e}')

conn.close()
