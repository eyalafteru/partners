"""Reset stuck GPT status"""
import sqlite3

conn = sqlite3.connect('partnercalc.db')
cursor = conn.cursor()

# Reset stuck GPT status
cursor.execute("UPDATE scan_campaigns SET gpt_match_status = NULL, gpt_match_processed = 0, gpt_match_total = 0 WHERE gpt_match_status = 'running'")
print(f'Reset {cursor.rowcount} campaigns')

conn.commit()
conn.close()
print("Done!")
