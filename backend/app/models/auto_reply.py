"""
PartnerCalc OS - Auto Reply Model
מודל הגדרות תשובה אוטומטית
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AutoReply(Base):
    """
    טבלת הגדרות Auto-Reply
    
    מצבים:
    - off: כבוי
    - suggest: AI מציע, אני מאשר
    - auto: AI עונה אוטומטית
    """
    __tablename__ = "auto_reply_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # WhatsApp
    whatsapp_enabled = Column(Boolean, default=True)
    whatsapp_mode = Column(String(20), default="suggest")  # off, suggest, auto
    whatsapp_delay_seconds = Column(Integer, default=30)
    
    # Email
    email_enabled = Column(Boolean, default=True)
    email_mode = Column(String(20), default="suggest")
    email_delay_seconds = Column(Integer, default=60)
    
    # SMS
    sms_enabled = Column(Boolean, default=False)
    sms_mode = Column(String(20), default="off")
    sms_delay_seconds = Column(Integer, default=60)
    
    # Business Hours
    business_hours_only = Column(Boolean, default=True)
    business_hours_start = Column(String(5), default="09:00")
    business_hours_end = Column(String(5), default="18:00")
    
    # Limits
    max_auto_replies_per_lead = Column(Integer, default=3)
    
    # Keywords for human escalation
    keywords_trigger_human = Column(JSON, default=[])
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<AutoReply(id={self.id}, whatsapp={self.whatsapp_mode})>"


class AutoReplySettings(Base):
    """
    Alias for backward compatibility
    """
    __tablename__ = "auto_reply_settings_legacy"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String(20), default="suggest")
    rules = Column(JSON, default={})
    delay_seconds = Column(Integer, default=30)
    max_auto_replies = Column(Integer, default=3)
    fallback_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PendingReply(Base):
    """
    טבלת תשובות ממתינות לאישור - תומכת בכל הערוצים.
    
    סטטוסים: pending, approved, rejected, auto_sent
    ערוצים: email, whatsapp, sms, facebook_comment, facebook_messenger
    """
    __tablename__ = "pending_replies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ערוץ התקשורת (email, whatsapp, sms, facebook_comment, facebook_messenger)
    channel = Column(String(30), default="email", comment="ערוץ: email, whatsapp, sms, facebook_comment, facebook_messenger")
    
    # קשר להודעה המקורית (אופציונלי - יכול להיות מתרחיש)
    communication_id = Column(Integer, ForeignKey("communication.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    
    # קשר לתגובת פייסבוק (אופציונלי)
    facebook_reply_id = Column(Integer, nullable=True, comment="מזהה FacebookReply אם הערוץ הוא פייסבוק")
    
    # מידע על התרחיש
    scenario_name = Column(String(100), comment="שם התרחיש שהתאים")
    scenario_category = Column(String(50), comment="קטגוריית התרחיש")
    match_confidence = Column(String(10), comment="רמת הביטחון בהתאמה")
    match_method = Column(String(20), comment="שיטת ההתאמה: gpt או keywords")
    
    # נושא התשובה המוצע
    suggested_subject = Column(String(500), comment="נושא המייל המוצע")
    
    # התשובה המוצעת
    suggested_reply = Column(Text, nullable=False)
    ai_reasoning = Column(Text, comment="למה ה-AI הציע את זה")
    
    # הודעת הטריגר המקורית (לתצוגה)
    trigger_message = Column(Text, comment="ההודעה שהפעילה את התרחיש")
    trigger_subject = Column(String(500), comment="נושא ההודעה המקורית")
    sender_email = Column(String(200), comment="כתובת השולח")
    sender_name = Column(String(200), comment="שם השולח")
    
    # סטטוס
    status = Column(String(20), default="pending")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relations
    communication = relationship("Communication", back_populates="pending_reply")
    lead = relationship("Lead")
    
    def __repr__(self):
        return f"<PendingReply(id={self.id}, channel='{self.channel}', status='{self.status}', scenario='{self.scenario_name}')>"
