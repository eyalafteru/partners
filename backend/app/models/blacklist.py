"""
PartnerCalc OS - Blacklist Model
מודל רשימה שחורה - מיילים/דומיינים שלא לשלוח אליהם
"""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Blacklist(Base):
    """
    רשימה שחורה - מיילים/דומיינים שלא לשלוח אליהם
    
    סיבות אפשריות:
    - bounced: מייל חזר
    - unsubscribed: ביקש להסרה
    - spam_complaint: התלונן על ספאם
    - manual: הוסף ידנית
    """
    __tablename__ = "blacklist"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # זיהוי
    email = Column(String(255), unique=True, nullable=True, index=True, comment="כתובת מייל ספציפית")
    domain = Column(String(255), nullable=True, index=True, comment="דומיין שלם לחסימה")
    
    # מידע
    reason = Column(String(100), nullable=False, comment="סיבת החסימה")
    notes = Column(Text, nullable=True, comment="הערות נוספות")
    
    # מקור
    source = Column(String(100), default="manual", comment="איך נוסף: manual, bounce, unsubscribe")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        identifier = self.email or self.domain
        return f"<Blacklist(id={self.id}, {identifier}, reason='{self.reason}')>"
