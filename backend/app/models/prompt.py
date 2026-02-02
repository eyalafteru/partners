"""
PartnerCalc OS - Prompt Model
מודל פרומפטים ולוגים של AI
"""
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Prompt(Base):
    """
    טבלת פרומפטים - ניהול פרומפטים לכל 9 צמתי ה-AI
    """
    __tablename__ = "prompts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # זיהוי
    node_name = Column(String(50), unique=True, nullable=False, comment="שם טכני: is_real_business, match_calculator...")
    display_name = Column(String(100), comment="שם תצוגה בעברית")
    description = Column(Text, comment="הסבר על הצומת")
    
    # פרומפטים
    system_prompt = Column(Text, comment="System prompt")
    user_prompt_template = Column(Text, comment="User prompt עם {{placeholders}}")
    
    # משתנים זמינים
    available_variables = Column(JSON, comment='["domain", "inner_text", "category"]')
    
    # הגדרות מודל
    model_name = Column(String(50), default="dictalm-atomic-v2-q4")
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=500)
    
    # סטטוס
    is_active = Column(Boolean, default=True)
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    ai_logs = relationship("AILog", back_populates="prompt")
    
    def __repr__(self):
        return f"<Prompt(id={self.id}, node_name='{self.node_name}')>"


class AILog(Base):
    """
    טבלת לוגים של AI - היסטוריית קריאות
    """
    __tablename__ = "ai_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # קשרים
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    
    # Input/Output
    input_data = Column(JSON, comment="הנתונים שהוזנו")
    full_prompt = Column(Text, comment="הפרומפט המלא אחרי החלפת משתנים")
    response = Column(Text, comment="תשובת ה-AI")
    response_parsed = Column(JSON, comment="התשובה מפורסרת")
    
    # ביצועים
    execution_time_ms = Column(Integer, comment="זמן ריצה במילישניות")
    tokens_used = Column(Integer, comment="כמות טוקנים")
    
    # סטטוס
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # תאריך
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relations
    prompt = relationship("Prompt", back_populates="ai_logs")
    
    def __repr__(self):
        return f"<AILog(id={self.id}, prompt_id={self.prompt_id}, success={self.success})>"
