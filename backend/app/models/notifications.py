"""
PartnerCalc OS - Notification Settings Model
ניהול התראות WhatsApp
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class NotificationPhone(Base):
    """מספרי טלפון לקבלת התראות WhatsApp"""
    __tablename__ = "notification_phones"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False, unique=True)
    name = Column(String(100), nullable=True)  # שם לזיהוי
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NotificationLog(Base):
    """לוג התראות שנשלחו"""
    __tablename__ = "notification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="sent")  # sent, failed
    error = Column(Text, nullable=True)
    related_email_id = Column(Integer, nullable=True)  # קשר למייל שגרם להתראה
    created_at = Column(DateTime(timezone=True), server_default=func.now())
