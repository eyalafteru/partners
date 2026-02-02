"""
PartnerCalc OS - Email Queue Model
מודל תור מיילים לשליחה מתוזמנת
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class EmailQueue(Base):
    """
    תור מיילים לשליחה מתוזמנת
    
    סטטוסים:
    - pending: ממתין לשליחה
    - sent: נשלח בהצלחה
    - failed: נכשל
    - cancelled: בוטל
    """
    __tablename__ = "email_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לליד
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    
    # קשר לתבנית (אופציונלי)
    template_id = Column(Integer, ForeignKey("email_templates.id"), nullable=True)
    
    # תוכן המייל
    to_email = Column(String(255), nullable=False, comment="כתובת הנמען")
    subject = Column(String(500), nullable=False, comment="נושא המייל")
    body = Column(Text, nullable=False, comment="תוכן המייל (HTML)")
    
    # תזמון
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True, comment="מועד שליחה מתוזמן")
    sent_at = Column(DateTime(timezone=True), nullable=True, comment="מועד שליחה בפועל")
    
    # סטטוס
    status = Column(String(50), default="pending", index=True)
    error_message = Column(Text, nullable=True, comment="הודעת שגיאה במקרה של כישלון")
    retry_count = Column(Integer, default=0, comment="מספר נסיונות שליחה חוזרת")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    lead = relationship("Lead", backref="email_queue_items")
    template = relationship("EmailTemplate")
    
    def __repr__(self):
        return f"<EmailQueue(id={self.id}, lead_id={self.lead_id}, status='{self.status}')>"
