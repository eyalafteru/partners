"""
PartnerCalc OS - Email Template Model
מודל תבניות מייל
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class EmailTemplate(Base):
    """
    טבלת תבניות מייל
    
    קטגוריות:
    - first_contact: פנייה ראשונה
    - follow_up: מעקב
    - response: תשובה
    - reminder: תזכורת
    - closing: סגירה
    """
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # פרטי התבנית
    name = Column(String(100), nullable=False, comment="שם התבנית")
    subject = Column(String(255), nullable=False, comment="נושא המייל (עם משתנים)")
    body_text = Column(Text, nullable=False, comment="גוף המייל - טקסט")
    body_html = Column(Text, nullable=True, comment="גוף המייל - HTML")
    
    # קטגוריה וסטטוס
    category = Column(String(50), default="first_contact", 
                     comment="first_contact, follow_up, response, reminder, closing")
    is_active = Column(Boolean, default=True, comment="האם התבנית פעילה")
    
    # משתנים זמינים בתבנית
    variables = Column(JSON, default=[], comment="רשימת משתנים בשימוש")
    
    # סטטיסטיקות
    usage_count = Column(Integer, default=0, comment="כמה פעמים נשלחה")
    total_opens = Column(Integer, default=0, comment="סה\"כ פתיחות")
    total_clicks = Column(Integer, default=0, comment="סה\"כ קליקים")
    
    # אחוזים מחושבים
    open_rate = Column(Float, default=0.0, comment="אחוז פתיחות")
    click_rate = Column(Float, default=0.0, comment="אחוז קליקים")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    communications = relationship("Communication", back_populates="template")
    
    def __repr__(self):
        return f"<EmailTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def update_stats(self, was_opened: bool = False, was_clicked: bool = False):
        """עדכון סטטיסטיקות התבנית"""
        self.usage_count += 1
        
        if was_opened:
            self.total_opens += 1
        if was_clicked:
            self.total_clicks += 1
        
        # חישוב אחוזים
        if self.usage_count > 0:
            self.open_rate = (self.total_opens / self.usage_count) * 100
            self.click_rate = (self.total_clicks / self.usage_count) * 100
