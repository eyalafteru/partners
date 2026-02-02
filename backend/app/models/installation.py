"""
PartnerCalc OS - Installation Model
מודל התקנות - ניטור מחשבונים מותקנים
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Installation(Base):
    """
    טבלת התקנות - מעקב אחרי מחשבונים שהותקנו באתרי שותפים
    """
    __tablename__ = "installations"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשרים
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    calc_id = Column(Integer, ForeignKey("calculators.id"), nullable=False)
    
    # מיקום ההתקנה
    embed_page_url = Column(String(500), nullable=False, comment="העמוד שבו הוטמע המחשבון")
    
    # סטטוס
    is_link_live = Column(Boolean, default=True, comment="האם הקישור עדיין קיים?")
    violation_count = Column(Integer, default=0, comment="כמה פעמים הוסר הקישור")
    
    # תאריכים
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    last_verified = Column(DateTime(timezone=True), comment="בדיקה אחרונה")
    removed_at = Column(DateTime(timezone=True), comment="תאריך הסרה (אם הוסר)")
    
    # Relations
    lead = relationship("Lead", back_populates="installations")
    calculator = relationship("Calculator", back_populates="installations")
    
    def __repr__(self):
        return f"<Installation(id={self.id}, lead_id={self.lead_id}, is_live={self.is_link_live})>"
