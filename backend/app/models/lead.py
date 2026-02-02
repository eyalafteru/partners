"""
PartnerCalc OS - Lead Model
מודל לידים (אתרים פוטנציאליים)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Lead(Base):
    """
    טבלת לידים - אתרים פוטנציאליים לשותפות
    
    סטטוסים:
    - new: חדש, עוד לא נסרק
    - scanned: נסרק
    - matched: נמצאה התאמה למחשבון
    - contacted: נשלחה פנייה
    - responded: התקבלה תגובה
    - installed: המחשבון הותקן
    - rejected: נדחה
    """
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # מידע על האתר
    domain = Column(String(255), unique=True, nullable=False, index=True, comment="דומיין האתר")
    site_name = Column(String(255), comment="שם האתר/העסק")
    category = Column(String(100), comment="קטגוריה: עורכי דין, רואי חשבון...")
    
    # פרטי קשר (JSON)
    contact_info = Column(JSON, default={}, comment="{email, phone, whatsapp, name}")
    
    # נתוני SEO (JSON)
    seo_data = Column(JSON, default={}, comment="{dr, monthly_traffic, backlinks}")
    
    # סטטוס AI (JSON)
    ai_status = Column(JSON, default={}, comment="{is_real, relevance_score, reasoning}")
    
    # סטטוס
    status = Column(String(50), default="new", index=True)
    
    # מחשבון מומלץ
    recommended_calc_id = Column(Integer, ForeignKey("calculators.id"), nullable=True)
    
    # מקור הליד
    source_campaign_id = Column(Integer, ForeignKey("scan_campaigns.id"), nullable=True)
    source_url = Column(String(500), comment="ה-URL המקורי מגוגל")
    google_position = Column(Integer, comment="מיקום בתוצאות גוגל")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_contacted_at = Column(DateTime(timezone=True), comment="תאריך פנייה אחרונה")
    last_response_at = Column(DateTime(timezone=True), comment="תאריך תגובה אחרונה")
    
    # מעקב Outreach
    outreach_count = Column(Integer, default=0, comment="מספר מיילים שנשלחו")
    
    # Relations
    recommended_calculator = relationship("Calculator", back_populates="leads")
    communications = relationship("Communication", back_populates="lead")
    installations = relationship("Installation", back_populates="lead")
    source_campaign = relationship("ScanCampaign", back_populates="leads")
    
    def __repr__(self):
        return f"<Lead(id={self.id}, domain='{self.domain}', status='{self.status}')>"
    
    @property
    def email(self) -> str:
        """קבלת מייל ראשון"""
        emails = self.contact_info.get("emails", [])
        return emails[0] if emails else None
    
    @property
    def phone(self) -> str:
        """קבלת טלפון ראשון"""
        phones = self.contact_info.get("phones", [])
        return phones[0] if phones else None
    
    @property
    def relevance_score(self) -> float:
        """ציון רלוונטיות מ-AI"""
        return self.ai_status.get("relevance_score", 0.0)
    
    @property
    def can_contact(self) -> bool:
        """
        האם ניתן לשלוח מייל לליד זה?
        True רק אם:
        - מעולם לא נפנה (last_contacted_at is None)
        - או שהשיב (last_response_at is not None)
        """
        # Never contacted
        if self.last_contacted_at is None:
            return True
        # Contacted but responded - can follow up
        if self.last_response_at is not None:
            return True
        # Contacted but never responded - BLOCKED
        return False