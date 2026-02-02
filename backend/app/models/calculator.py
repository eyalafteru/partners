"""
PartnerCalc OS - Calculator Model
מודל מחשבונים
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Calculator(Base):
    """
    טבלת מחשבונים - 23 המחשבונים שלך
    """
    __tablename__ = "calculators"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # מידע בסיסי
    name = Column(String(255), nullable=False, comment="שם המחשבון")
    target_url = Column(String(500), nullable=False, comment="קישור לעמוד המחשבון")
    category = Column(String(100), default="הלוואות ומימון", comment="קטגוריית המחשבון")
    
    # מידע ל-AI
    intent_description = Column(Text, comment="תיאור מפורט - למי זה מתאים?")
    keywords = Column(JSON, comment="מילות מפתח לחיפוש וסיווג")
    
    # תקציר AI - נוצר אוטומטית מסריקת עמוד המחשבון
    ai_summary = Column(Text, comment="תקציר AI של מה המחשבון עושה ולמי מתאים")
    scraped_content = Column(Text, comment="תוכן שנסרק מעמוד המחשבון")
    scraped_at = Column(DateTime(timezone=True), comment="מתי נסרק העמוד")
    
    # קוד הטמעה
    embed_code_template = Column(Text, comment="קוד HTML/JS להטמעה")
    
    # סטטוס
    is_active = Column(Boolean, default=True, comment="האם המחשבון פעיל?")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    leads = relationship("Lead", back_populates="recommended_calculator")
    installations = relationship("Installation", back_populates="calculator")
    
    def __repr__(self):
        return f"<Calculator(id={self.id}, name='{self.name}')>"
