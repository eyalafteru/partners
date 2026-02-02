"""
Add GPT Match Fields to Database
מוסיף שדות חדשים להתאמת GPT - רק הוספה, ללא מחיקה!
"""
import sqlite3
from datetime import datetime

def add_gpt_fields():
    """Add GPT matching fields to database tables"""
    conn = sqlite3.connect('partnercalc.db')
    cursor = conn.cursor()
    
    print("=" * 50)
    print("Adding GPT Match Fields to Database")
    print("=" * 50)
    
    # ========== ScanQueue (per site) ==========
    scan_queue_fields = [
        ("gpt_recommended_calc_id", "INTEGER"),
        ("gpt_recommended_calc_score", "REAL"),
        ("gpt_recommended_calc_reason", "TEXT"),
        ("gpt_all_recommended_calcs", "TEXT"),
        ("gpt_matched_at", "TIMESTAMP"),
        ("gpt_match_duration_seconds", "REAL"),
        ("gpt_suggested_new_calc", "TEXT"),
    ]
    
    print("\n📊 Adding fields to scan_queue table:")
    for field_name, field_type in scan_queue_fields:
        try:
            cursor.execute(f"ALTER TABLE scan_queue ADD COLUMN {field_name} {field_type}")
            print(f"  ✅ Added: {field_name} ({field_type})")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  ⏭️ Already exists: {field_name}")
            else:
                print(f"  ❌ Error adding {field_name}: {e}")
    
    # ========== ScanCampaign (per campaign) ==========
    scan_campaign_fields = [
        ("gpt_match_status", "VARCHAR(20)"),
        ("gpt_match_processed", "INTEGER DEFAULT 0"),
        ("gpt_match_total", "INTEGER DEFAULT 0"),
    ]
    
    print("\n📊 Adding fields to scan_campaigns table:")
    for field_name, field_type in scan_campaign_fields:
        try:
            cursor.execute(f"ALTER TABLE scan_campaigns ADD COLUMN {field_name} {field_type}")
            print(f"  ✅ Added: {field_name} ({field_type})")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  ⏭️ Already exists: {field_name}")
            else:
                print(f"  ❌ Error adding {field_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 50)
    print("✅ GPT Fields Migration Complete!")
    print("=" * 50)

if __name__ == "__main__":
    add_gpt_fields()
