"""
PartnerCalc OS - API Key Model
מודל ניהול API Keys
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class ApiKey(Base):
    """
    טבלת API Keys - ניהול טוקנים של שירותים חיצוניים
    
    שירותים: whatsapp, sendgrid, twilio, apify, proxy, ollama
    
    הערה: credentials מוצפנים עם Fernet (AES-128)!
    """
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # זיהוי
    service_name = Column(String(50), unique=True, nullable=False, comment="whatsapp, sendgrid, twilio...")
    display_name = Column(String(100), comment="שם תצוגה")
    
    # Credentials (מוצפנים!)
    encrypted_credentials = Column(Text, comment="Fernet encrypted JSON")
    
    # סטטוס
    is_active = Column(Boolean, default=True)
    last_verified = Column(DateTime(timezone=True), comment="בדיקת חיבור אחרונה")
    last_error = Column(Text, comment="שגיאה אחרונה")
    
    # סטטיסטיקות שימוש
    usage_stats = Column(JSON, default={}, comment='{"calls_today": 100, "quota": 1000}')
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ApiKey(id={self.id}, service='{self.service_name}', active={self.is_active})>"
