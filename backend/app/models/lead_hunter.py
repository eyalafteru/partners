"""
PartnerCalc OS - Lead Hunter Models
מודלים למערכת Lead Hunter AI - קליטת פוסטים מפייסבוק, סיווג וניהול לידים
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base

VALID_AREAS = ["מרכז", "שרון", "שפלה", "ירושלים", "צפון", "דרום", "לא ידוע"]


class LeadArea(Base):
    """
    הגדרות לפי אזור גיאוגרפי - שליטה על תגובות AI והתראות WhatsApp
    """
    __tablename__ = "lead_areas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    # שליטה על מה המערכת עושה לפוסטים מאזור זה
    is_reply_enabled = Column(Boolean, default=True)       # ייצר תגובת AI
    is_whatsapp_enabled = Column(Boolean, default=True)    # שלח התראת WhatsApp
    is_visible = Column(Boolean, default=True)             # הצג בדשבורד

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<LeadArea(id={self.id}, name='{self.name}')>"


class LeadCategory(Base):
    """
    קטגוריות סיווג לידים - כל קטגוריה מכילה פרומפט ומספר טלפון להתראה
    
    קטגוריות מובנות:
    1 - חיפוש הובלת פריט בודד/משרד       → רלוונטי ✅
    2 - חיפוש הלוואה פרטית/מימון נכס      → רלוונטי ✅
    3 - חיפוש הלוואה עסקית                → רלוונטי ✅
    4 - פרסום חברת הובלות/מוביל (מתחרה)   → לא שולחים התראה ❌
    5 - חיפוש נכס מסחרי/משרד              → רלוונטי ✅
    0 - לא רלוונטי                        → ❌
    """
    __tablename__ = "lead_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)

    # פרומפט לסיווג ויצירת תגובה
    classification_prompt = Column(Text, nullable=False)
    reply_prompt = Column(Text)

    # WhatsApp
    whatsapp_phone = Column(String(20), nullable=True)
    whatsapp_name = Column(String(100), nullable=True)

    # האם לשלוח התראה WhatsApp לקטגוריה זו
    is_alert_worthy = Column(Boolean, default=True)

    # תשתית לתגובה אוטומטית עתידית
    auto_reply_enabled = Column(Boolean, default=False)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    posts = relationship("LeadPost", back_populates="category")

    def __repr__(self):
        return f"<LeadCategory(id={self.id}, name='{self.name}')>"


class LeadActor(Base):
    """
    פרופילי משתמשים שפרסמו פוסטים - עם מונה פוסטים לזיהוי ספאמרים/לידים חמים
    """
    __tablename__ = "lead_actors"

    id = Column(Integer, primary_key=True, index=True)

    actor_url = Column(String(500), unique=True, nullable=False, index=True)
    actor_name = Column(String(255), nullable=False)

    # מונה פוסטים מצטבר - עולה בכל פוסט חדש מאותו משתמש
    post_count = Column(Integer, default=1)

    last_activity_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    posts = relationship("LeadPost", back_populates="actor")

    def __repr__(self):
        return f"<LeadActor(id={self.id}, name='{self.actor_name}', posts={self.post_count})>"


class LeadPost(Base):
    """
    פוסטים שנקלטו מגיליון הדרייב - לידים נכנסים מקבוצות פייסבוק
    
    סטטוסים:
    - new: נקלט, ממתין לסיווג AI
    - classified: סווג ע"י AI
    - notified: נשלחה התראה WhatsApp
    - replied: המנהל ענה/פעל
    - ignored: סומן כ"לא רלוונטי"
    """
    __tablename__ = "lead_posts"

    id = Column(Integer, primary_key=True, index=True)

    # מזהה ייחודי - לינק לפוסט
    post_url = Column(String(1000), unique=True, nullable=False, index=True)

    # תוכן הפוסט
    description = Column(Text, nullable=False)
    posted_at = Column(DateTime(timezone=True))

    # קבוצה
    group_name = Column(String(255))
    group_url = Column(String(500))

    # קשר לActor
    actor_id = Column(Integer, ForeignKey("lead_actors.id"), nullable=True)

    # קשר לקטגוריה (0 = לא רלוונטי, NULL = טרם סווג)
    category_id = Column(Integer, ForeignKey("lead_categories.id"), nullable=True)

    # תגובה מוצעת ע"י AI
    ai_reply = Column(Text)

    # מידע AI
    ai_confidence = Column(Float)
    ai_reasoning = Column(Text)

    # סטטוס: new, classified, notified, replied, ignored
    status = Column(String(20), default="new")

    # מעקב WhatsApp
    whatsapp_sent = Column(Boolean, default=False)
    whatsapp_sent_at = Column(DateTime(timezone=True))
    whatsapp_replied = Column(Boolean, default=False)
    whatsapp_replied_at = Column(DateTime(timezone=True))

    # אזור גיאוגרפי שזוהה על ידי AI
    area = Column(String(50), nullable=True)

    # תשתית לתגובה אוטומטית עתידית
    auto_reply_enabled = Column(Boolean, default=False)
    auto_reply_sent = Column(Boolean, default=False)
    auto_reply_sent_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relations
    actor = relationship("LeadActor", back_populates="posts")
    category = relationship("LeadCategory", back_populates="posts")
    feedback = relationship("AIFeedback", back_populates="post")

    def __repr__(self):
        return f"<LeadPost(id={self.id}, status='{self.status}', category={self.category_id})>"


class AIFeedback(Base):
    """
    Feedback Loop - שמירת תיקונים ידניים לשיפור הפרומפט
    
    כל פוסט שמסומן כ"לא רלוונטי" או שסיווגו תוקן ידנית נשמר כאן.
    ה-Negative Examples האלה מוזנים לתוך ה-System Prompt בסיווג הבא.
    """
    __tablename__ = "ai_feedback"

    id = Column(Integer, primary_key=True, index=True)

    post_id = Column(Integer, ForeignKey("lead_posts.id"), nullable=False)

    # הסיווג המקורי של ה-AI
    original_category_id = Column(Integer, nullable=True)

    # הסיווג הנכון (אם תוקן ידנית)
    corrected_category_id = Column(Integer, nullable=True)

    # האם סומן כ"לא רלוונטי" לחלוטין
    is_irrelevant = Column(Boolean, default=False)

    # הערת המנהל
    note = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    post = relationship("LeadPost", back_populates="feedback")

    def __repr__(self):
        return f"<AIFeedback(id={self.id}, post_id={self.post_id}, irrelevant={self.is_irrelevant})>"
