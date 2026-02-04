"""Import all Facebook groups from JSON file"""
import requests
import json

# קרא את הקבוצות מהקובץ
with open('full_groups.json', 'r', encoding='utf-8') as f:
    groups_data = json.load(f)

print(f"נמצאו {len(groups_data)} קבוצות לייבוא...")

# שלח לשרת
API_URL = "https://partners.ppcmedia.co.il/api/facebook/groups/bulk-import"

try:
    response = requests.post(
        API_URL,
        json={"groups": groups_data},
        verify=False,  # Skip SSL verification for self-signed cert
        timeout=120
    )
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"✅ יובאו: {result['imported']} קבוצות חדשות")
    print(f"⏭️ דולגו (כבר קיימות): {result['skipped']} קבוצות")
    print(f"📊 סה\"כ: {result['total']} קבוצות")
except Exception as e:
    print(f"❌ Error: {e}")
