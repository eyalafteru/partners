"""Update lead email from Gmail to afteru.co.il"""
import sqlite3

def update_lead():
    old_email = "afterunew@gmail.com"
    new_email = "eyal@afteru.co.il"
    
    conn = sqlite3.connect("partnercalc.db")
    cursor = conn.cursor()
    
    # Update using replace
    cursor.execute(
        "UPDATE leads SET contact_info = replace(contact_info, ?, ?) WHERE contact_info LIKE ?",
        (old_email, new_email, f"%{old_email}%")
    )
    
    conn.commit()
    print(f"Updated {cursor.rowcount} leads")
    conn.close()

if __name__ == "__main__":
    update_lead()
