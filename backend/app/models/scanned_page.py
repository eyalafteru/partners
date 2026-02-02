"""
PartnerCalc OS - Scanned Page Model
מודל לשמירת עמודים שנסרקו מאתרים (סריקה מעמיקה)
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class ScannedPage(Base):
    """
    טבלת עמודים סרוקים - עמודים פנימיים שנסרקו מאתרים
    
    כל אתר יכול להכיל מספר עמודים סרוקים (דף הבית, אודות, שירותים, צור קשר...)
    """
    __tablename__ = "scanned_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשר לאתר המקורי ב-ScanQueue
    queue_item_id = Column(Integer, ForeignKey("scan_queue.id"), nullable=False, index=True)
    
    # פרטי העמוד
    url = Column(String(500), nullable=False, comment="URL מלא של העמוד")
    path = Column(String(255), comment="נתיב יחסי: /about, /contact...")
    page_type = Column(String(50), comment="סוג: home, about, services, contact, blog, pricing, other")
    title = Column(String(500), comment="כותרת העמוד")
    
    # תוכן
    html_text = Column(Text, comment="טקסט נקי מהעמוד")
    
    # זיהוי טופס יצירת קשר
    has_contact_form = Column(Boolean, default=False, comment="האם יש טופס יצירת קשר")
    form_selector = Column(String(255), comment="CSS selector של הטופס")
    form_html = Column(Text, comment="HTML של הטופס")
    
    # סטטוס
    status = Column(String(20), default="scraped", comment="scraped, failed")
    error_message = Column(Text, comment="הודעת שגיאה אם נכשל")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    queue_item = relationship("ScanQueue", back_populates="scanned_pages")
    
    def __repr__(self):
        return f"<ScannedPage(id={self.id}, path='{self.path}', type='{self.page_type}')>"
    
    @property
    def is_contact_page(self) -> bool:
        """האם זה עמוד צור קשר"""
        return self.page_type == "contact" or self.has_contact_form
