"""
PartnerCalc OS - AI Service
שכבת שירות לכל פעולות ה-AI
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.ai.ollama_client import OllamaClientWithPrompts
from app.models.calculator import Calculator
from app.models.lead import Lead


class AIService:
    """
    שירות AI מרכזי - מעטפת לכל 9 צמתי ה-AI
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.client = OllamaClientWithPrompts(session=session)
    
    # ========== צומת 1: סינון עסק אמיתי ==========
    
    async def is_real_business(
        self,
        domain: str,
        inner_text: str,
        lead_id: int = None
    ) -> Dict[str, Any]:
        """
        בדיקה האם האתר שייך לעסק אמיתי
        
        Returns:
            {
                "is_real": True/False,
                "confidence": 0.0-1.0,
                "business_type": "סוג העסק",
                "reasoning": "הסבר"
            }
        """
        logger.info(f"Checking if {domain} is real business")
        
        # חיתוך הטקסט לאורך סביר
        truncated_text = inner_text[:5000] if inner_text else ""
        
        return await self.client.execute_prompt(
            node_name="is_real_business",
            variables={
                "domain": domain,
                "inner_text": truncated_text
            },
            lead_id=lead_id
        )
    
    # ========== צומת 2: התאמת מחשבון ==========
    
    async def match_calculator(
        self,
        page_content: str,
        calculators: List[Dict],
        lead_id: int = None
    ) -> Dict[str, Any]:
        """
        התאמת המחשבון הטוב ביותר לאתר
        
        Returns:
            {
                "calc_id": 1,
                "calc_name": "שם המחשבון",
                "match_score": 0.0-1.0,
                "reasoning": "למה זה מתאים"
            }
        """
        import json
        
        logger.info(f"Matching calculator for content ({len(page_content)} chars)")
        
        # הכנת רשימת מחשבונים
        calcs_json = json.dumps(
            [{"id": c["id"], "name": c["name"], "description": c.get("intent_description", "")} 
             for c in calculators],
            ensure_ascii=False
        )
        
        return await self.client.execute_prompt(
            node_name="match_calculator",
            variables={
                "page_content": page_content[:3000],
                "calculators_json": calcs_json
            },
            lead_id=lead_id
        )
    
    # ========== צומת 3: חילוץ פרטי קשר ==========
    
    async def extract_contact(
        self,
        html_content: str,
        domain: str,
        lead_id: int = None
    ) -> Dict[str, Any]:
        """
        חילוץ פרטי קשר מהאתר
        
        Returns:
            {
                "emails": ["email1@domain.com"],
                "phones": ["03-1234567"],
                "whatsapp": "+972501234567",
                "contact_name": "שם"
            }
        """
        logger.info(f"Extracting contact from {domain}")
        
        return await self.client.execute_prompt(
            node_name="extract_contact",
            variables={
                "html_content": html_content[:8000],
                "domain": domain
            },
            lead_id=lead_id
        )
    
    # ========== צומת 4: ניסוח WhatsApp ==========
    
    async def generate_whatsapp(
        self,
        lead: Lead,
        calculator: Calculator
    ) -> str:
        """
        יצירת הודעת WhatsApp מותאמת אישית
        
        Returns:
            תוכן ההודעה
        """
        logger.info(f"Generating WhatsApp for {lead.domain}")
        
        result = await self.client.execute_prompt(
            node_name="generate_whatsapp",
            variables={
                "site_name": lead.site_name or lead.domain,
                "domain": lead.domain,
                "category": lead.category or "כללי",
                "relevant_content": lead.ai_status.get("reasoning", "") if lead.ai_status else "",
                "calculator_name": calculator.name,
                "calculator_description": calculator.intent_description or "",
                "calculator_url": calculator.target_url
            },
            lead_id=lead.id
        )
        
        return result.get("message", "")
    
    # ========== צומת 5: ניסוח Email ==========
    
    async def generate_email(
        self,
        lead: Lead,
        calculator: Calculator,
        contact_name: str = None
    ) -> Dict[str, str]:
        """
        יצירת מייל מותאם אישית
        
        Returns:
            {"subject": "נושא", "body": "גוף המייל"}
        """
        logger.info(f"Generating Email for {lead.domain}")
        
        result = await self.client.execute_prompt(
            node_name="generate_email",
            variables={
                "site_name": lead.site_name or lead.domain,
                "domain": lead.domain,
                "category": lead.category or "כללי",
                "relevant_content": lead.ai_status.get("reasoning", "") if lead.ai_status else "",
                "contact_name": contact_name or "בעל/ת האתר",
                "calculator_name": calculator.name,
                "calculator_description": calculator.intent_description or "",
                "calculator_url": calculator.target_url
            },
            lead_id=lead.id
        )
        
        return {
            "subject": result.get("subject", "הצעת שיתוף פעולה"),
            "body": result.get("body", "")
        }
    
    # ========== צומת 6: ניסוח SMS ==========
    
    async def generate_sms(
        self,
        lead: Lead,
        calculator: Calculator,
        short_url: str = None
    ) -> str:
        """
        יצירת הודעת SMS (עד 160 תווים)
        
        Returns:
            תוכן ההודעה
        """
        logger.info(f"Generating SMS for {lead.domain}")
        
        result = await self.client.execute_prompt(
            node_name="generate_sms",
            variables={
                "site_name": lead.site_name or lead.domain,
                "calculator_name": calculator.name,
                "short_url": short_url or calculator.target_url
            },
            lead_id=lead.id
        )
        
        message = result.get("message", "")
        
        # וידוא אורך
        if len(message) > 160:
            message = message[:157] + "..."
        
        return message
    
    # ========== צומת 7: ניתוח תגובה ==========
    
    async def analyze_response(
        self,
        message_body: str,
        lead_id: int = None
    ) -> Dict[str, Any]:
        """
        ניתוח הודעה נכנסת
        
        Returns:
            {
                "sentiment": "positive/negative/neutral",
                "intent": "interested/not_interested/asking_questions/...",
                "urgency": "high/medium/low",
                "needs_human": True/False,
                "summary": "סיכום"
            }
        """
        logger.info(f"Analyzing response: {message_body[:50]}...")
        
        return await self.client.execute_prompt(
            node_name="analyze_response",
            variables={
                "message_body": message_body,
                "context": "תגובה להצעת שיתוף פעולה להטמעת מחשבון"
            },
            lead_id=lead_id
        )
    
    # ========== צומת 8: הצעת תשובה ==========
    
    async def suggest_reply(
        self,
        conversation_history: str,
        last_message: str,
        analysis: Dict[str, Any],
        lead_id: int = None
    ) -> Dict[str, str]:
        """
        הצעת תשובה להודעה
        
        Returns:
            {
                "reply": "התשובה המוצעת",
                "reasoning": "למה"
            }
        """
        import json
        
        logger.info(f"Suggesting reply for: {last_message[:50]}...")
        
        return await self.client.execute_prompt(
            node_name="suggest_reply",
            variables={
                "conversation_history": conversation_history,
                "last_message": last_message,
                "analysis": json.dumps(analysis, ensure_ascii=False)
            },
            lead_id=lead_id
        )
    
    # ========== צומת 9: זיהוי שדות טופס ==========
    
    async def identify_form_fields(
        self,
        form_html: str,
        our_name: str,
        our_email: str,
        our_phone: str,
        our_message: str
    ) -> Dict[str, Any]:
        """
        זיהוי שדות בטופס צור קשר
        
        Returns:
            {
                "fields": [{"selector": "...", "value": "..."}],
                "submit_selector": "button[type=submit]"
            }
        """
        logger.info(f"Identifying form fields")
        
        return await self.client.execute_prompt(
            node_name="identify_form_fields",
            variables={
                "form_html": form_html[:5000],
                "our_name": our_name,
                "our_email": our_email,
                "our_phone": our_phone,
                "our_message": our_message
            }
        )


async def get_ai_service(session: AsyncSession) -> AIService:
    """
    Factory function לקבלת AIService
    """
    return AIService(session)
