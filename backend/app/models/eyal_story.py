"""
PartnerCalc OS - Eyal Story Model
מודל לשמירת הסיפור של אייל עובדיה לשימוש ב-AI
"""
from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func

from app.database import Base


class EyalStory(Base):
    """
    טבלה בודדת לשמירת הסיפור של אייל
    תמיד יש רק שורה אחת (id=1)
    """
    __tablename__ = "eyal_story"
    
    id = Column(Integer, primary_key=True, default=1, comment="תמיד 1 - שורה בודדת")
    
    # הסיפור המלא - טקסט אחד גדול לעריכה
    story_content = Column(
        Text, 
        nullable=False,
        comment="הסיפור המלא של אייל - טקסט חופשי לעריכה"
    )
    
    # משפטים אסורים - שורה לכל משפט
    forbidden_phrases = Column(
        Text, 
        nullable=True,
        comment="משפטים שה-AI לא ישתמש בהם - שורה לכל משפט"
    )
    
    # הוראות נוספות ל-AI
    ai_instructions = Column(
        Text, 
        nullable=True,
        comment="הוראות נוספות ל-AI לגבי יצירת תוכן"
    )
    
    # תאריכים
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        content_preview = self.story_content[:50] if self.story_content else "Empty"
        return f"<EyalStory(id={self.id}, content='{content_preview}...')>"
    
    def get_full_prompt(self) -> str:
        """
        מחזיר את הפרומפט המלא לשימוש ב-AI
        כולל מאגר עובדות מקטגוריות, משפטים אסורים והוראות נוספות
        """
        prompt_parts = []
        
        # הנחיית מאגר עובדות
        prompt_parts.append("═══════════════════════════════════════════════════════════")
        prompt_parts.append("     מאגר העובדות של אייל עובדיה - בחר 1-2 עובדות לכל פוסט!")
        prompt_parts.append("═══════════════════════════════════════════════════════════")
        prompt_parts.append("")
        prompt_parts.append("הנחיות בחירת עובדות:")
        prompt_parts.append("• לכל פוסט בחר 1-2 עובדות מקטגוריות שונות")
        prompt_parts.append("• אל תשתמש באותה קומבינציה פעמיים")
        prompt_parts.append("• שלב את העובדה בצורה טבעית עם הצעת המחשבון")
        prompt_parts.append("• אם יש פוסטים קודמים - חובה לבחור עובדות אחרות!")
        prompt_parts.append("")
        
        # הסיפור המלא (מחולק לקטגוריות ע"י המשתמש בפרונט)
        prompt_parts.append(self.story_content or "")
        prompt_parts.append("")
        
        # משפטים אסורים
        if self.forbidden_phrases:
            prompt_parts.append("═══════════════════════════════════════════════════════════")
            prompt_parts.append("⛔ משפטים אסורים - אל תשתמש בהם!")
            prompt_parts.append("═══════════════════════════════════════════════════════════")
            prompt_parts.append("")
            for phrase in self.forbidden_phrases.strip().split('\n'):
                if phrase.strip():
                    prompt_parts.append(f"• אסור: \"{phrase.strip()}\"")
            prompt_parts.append("")
        
        # הוראות נוספות
        if self.ai_instructions:
            prompt_parts.append("═══════════════════════════════════════════════════════════")
            prompt_parts.append("📝 הוראות נוספות")
            prompt_parts.append("═══════════════════════════════════════════════════════════")
            prompt_parts.append("")
            prompt_parts.append(self.ai_instructions)
            prompt_parts.append("")
        
        # אזהרה סופית - קצרה וממוקדת
        prompt_parts.append("═══════════════════════════════════════════════════════════")
        prompt_parts.append("⚠️ אזהרות: אסור להמציא עובדות/מספרים! אסור להשתמש במשפטים האסורים!")
        prompt_parts.append("═══════════════════════════════════════════════════════════")
        
        return "\n".join(prompt_parts)
