"""
יצירת טבלאות התראות WhatsApp
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base
from app.models.notifications import NotificationPhone, NotificationLog

def create_tables():
    """יצירת הטבלאות"""
    print("Creating notification tables...")
    
    # Create tables
    NotificationPhone.__table__.create(engine, checkfirst=True)
    NotificationLog.__table__.create(engine, checkfirst=True)
    
    print("✅ Tables created!")
    
    # Add default phone number
    from sqlalchemy.orm import Session
    from app.models.notifications import NotificationPhone
    
    with Session(engine) as session:
        existing = session.query(NotificationPhone).filter_by(phone="972542575411").first()
        if not existing:
            phone = NotificationPhone(
                phone="972542575411",
                name="אייל",
                is_active=True
            )
            session.add(phone)
            session.commit()
            print("✅ Default phone added: 972542575411")
        else:
            print("Phone already exists")

if __name__ == "__main__":
    create_tables()
