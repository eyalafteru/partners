"""
PartnerCalc OS - Communication Model
מודל תקשורת (הודעות WhatsApp, Email, SMS)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Communication(Base):
    """
    טבלת תקשורת - כל ההודעות בכל הערוצים
    
    ערוצים: whatsapp, email, sms
    כיוון: inbound (נכנס), outbound (יוצא)
    סטטוסים: pending, sent, delivered, read, replied, failed
    """
    __tablename__ = "communication"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לליד
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    
    # ערוץ וכיוון
    channel = Column(String(20), nullable=False, comment="whatsapp, email, sms")
    direction = Column(String(10), nullable=False, comment="inbound, outbound")
    
    # תוכן ההודעה
    message_body = Column(Text, nullable=False)
    subject = Column(String(255), comment="נושא - רלוונטי למייל בלבד")
    
    # סטטוס
    status = Column(String(20), default="pending", comment="pending, sent, delivered, read, replied, failed")
    
    # מטא-דאטה
    external_id = Column(String(100), comment="ID מהשירות החיצוני (SendGrid, Green-API, Twilio...)")
    error_message = Column(Text, comment="הודעת שגיאה אם נכשל")
    
    # האם נשלח אוטומטית
    is_auto_reply = Column(Boolean, default=False, comment="האם זו תשובה אוטומטית של AI")
    
    # ========== Email Specific ==========
    # קשר לתבנית מייל
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True, comment="תבנית ששימשה לשליחה")
    
    # מעקב אימייל
    opens_count = Column(Integer, default=0, comment="כמה פעמים נפתח המייל")
    clicks = Column(JSON, default=[], comment="רשימת לינקים שנלחצו")
    
    # Threading - קישור בין הודעות
    thread_id = Column(String(100), comment="מזהה שרשור לקיבוץ הודעות")
    in_reply_to_id = Column(Integer, ForeignKey("communication.id"), nullable=True, comment="הודעה שזו תשובה אליה")
    
    # תאריכים
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    delivered_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    
    # Relations
    lead = relationship("Lead", back_populates="communications")
    pending_reply = relationship("PendingReply", back_populates="communication", uselist=False)
    template = relationship("EmailTemplate", back_populates="communications")
    replies = relationship("Communication", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<Communication(id={self.id}, channel='{self.channel}', direction='{self.direction}')>"
