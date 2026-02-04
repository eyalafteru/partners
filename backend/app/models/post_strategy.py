"""
PartnerCalc OS - Post Strategy Model
מודל אסטרטגיות כתיבה לפוסטים
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func

from app.database import Base


class PostStrategy(Base):
    """
    טבלת אסטרטגיות כתיבה - 10 אסטרטגיות מובנות + אפשרות להוסיף
    """
    __tablename__ = "post_strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # מידע בסיסי
    name = Column(String(100), nullable=False, comment="שם האסטרטגיה")
    slug = Column(String(50), unique=True, nullable=False, index=True, comment="מזהה ייחודי")
    icon = Column(String(10), comment="אימוג'י")
    description = Column(String(255), comment="תיאור קצר")
    
    # תוכן ל-AI
    system_prompt = Column(Text, comment="הנחיות ל-AI")
    post_template = Column(Text, comment="תבנית עם משתנים: {calculator_name}, {calculator_url}")
    example_post = Column(Text, comment="דוגמה לפוסט")
    
    # הגדרות
    is_active = Column(Boolean, default=True, comment="האם האסטרטגיה פעילה")
    sort_order = Column(Integer, default=0, comment="סדר תצוגה")
    
    # סטטיסטיקות
    times_used = Column(Integer, default=0, comment="מספר פעמים שנעשה שימוש")
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<PostStrategy(id={self.id}, name='{self.name}', slug='{self.slug}')>"
