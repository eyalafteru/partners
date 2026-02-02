"""
PartnerCalc OS - Reply Scenario Model
מודל תרחישי תשובות אוטומטיות
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class ReplyScenario(Base):
    """
    טבלת תרחישי תשובות אוטומטיות
    
    Categories:
    - positive: תגובות חיוביות (מעוניין, איך מטמיעים, וכו')
    - negative: תגובות שליליות (לא מעוניין, הסר)
    - question: שאלות (למה חינם, מי אתם)
    - technical: שאלות טכניות (וורדפרס, וויקס)
    - deferral: דחייה זמנית (לא עכשיו)
    - human: דורש העברה לאנושי (בעיה, רוצה לדבר)
    """
    __tablename__ = "reply_scenarios"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # זיהוי התרחיש
    name = Column(String(100), unique=True, nullable=False, comment="מזהה טכני: interested_general")
    display_name = Column(String(200), nullable=False, comment="שם תצוגה: מעוניין בכללי")
    category = Column(String(50), nullable=False, default="positive", 
                      comment="positive/negative/question/technical/deferral/human")
    
    # מילות מפתח לזיהוי
    keywords = Column(JSON, default=[], comment="רשימת מילות מפתח לזיהוי התרחיש")
    
    # תבנית התשובה
    response_subject = Column(Text, comment="נושא המייל - תומך ב-{{variables}}")
    response_body = Column(Text, nullable=False, comment="גוף המייל - תומך ב-{{variables}}")
    
    # הגדרות
    requires_human = Column(Boolean, default=False, comment="האם להעביר לטיפול אנושי")
    priority = Column(Integer, default=50, comment="עדיפות - גבוה יותר = בודקים קודם")
    is_active = Column(Boolean, default=True, comment="האם התרחיש פעיל")
    
    # פרטי השולח
    sender_name = Column(String(100), default="אייל עובדיה", comment="שם השולח")
    sender_title = Column(String(200), default="מנהל מקצועי | רק תבקש", comment="תפקיד השולח")
    
    # מטא
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ReplyScenario(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "keywords": self.keywords or [],
            "response_subject": self.response_subject,
            "response_body": self.response_body,
            "requires_human": self.requires_human,
            "priority": self.priority,
            "is_active": self.is_active,
            "sender_name": self.sender_name,
            "sender_title": self.sender_title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
