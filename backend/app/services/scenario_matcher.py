"""
PartnerCalc OS - Scenario Matcher Service
שירות התאמת תרחישים למיילים נכנסים
"""
import json
import re
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.orm import Session
from loguru import logger

from app.models.reply_scenario import ReplyScenario
from app.ai.openai_client import get_openai_client


class ScenarioMatcher:
    """
    שירות התאמת תרחישים למיילים נכנסים
    משתמש ב-GPT לזיהוי חכם + fallback למילות מפתח
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.openai = get_openai_client()
    
    async def match_scenario(
        self,
        email_subject: str,
        email_body: str,
        lead_domain: str = None
    ) -> Tuple[Optional[ReplyScenario], float, str]:
        """
        מתאים תרחיש למייל נכנס
        
        Args:
            email_subject: נושא המייל
            email_body: תוכן המייל
            lead_domain: דומיין הליד (אופציונלי)
        
        Returns:
            Tuple of (matched_scenario, confidence, method)
            - matched_scenario: התרחיש שנמצא (או None)
            - confidence: רמת הביטחון (0-1)
            - method: שיטת הזיהוי ("gpt" או "keywords")
        """
        # טעינת תרחישים פעילים
        scenarios = self.db.query(ReplyScenario).filter(
            ReplyScenario.is_active == True
        ).order_by(ReplyScenario.priority.desc()).all()
        
        if not scenarios:
            logger.warning("No active scenarios found")
            return None, 0, "none"
        
        # ניסיון ראשון: GPT
        try:
            scenario, confidence = await self._match_with_gpt(
                email_subject, email_body, scenarios
            )
            if scenario and confidence >= 0.7:
                logger.info(f"✅ GPT matched scenario: {scenario.name} (confidence: {confidence:.2f})")
                return scenario, confidence, "gpt"
        except Exception as e:
            logger.warning(f"GPT matching failed: {e}")
        
        # Fallback: מילות מפתח
        scenario, confidence = self._match_with_keywords(
            email_subject, email_body, scenarios
        )
        if scenario and confidence >= 0.5:
            logger.info(f"✅ Keywords matched scenario: {scenario.name} (confidence: {confidence:.2f})")
            return scenario, confidence, "keywords"
        
        # Fallback אחרון: תרחיש GPT מותאם אישית
        fallback = self.db.query(ReplyScenario).filter(
            ReplyScenario.name == "gpt_fallback",
            ReplyScenario.is_active == True
        ).first()
        
        if fallback:
            logger.info("🤖 Using GPT fallback scenario for custom response")
            return fallback, 0.5, "gpt_fallback"
        
        logger.info("No scenario matched")
        return None, 0, "none"
    
    async def _match_with_gpt(
        self,
        email_subject: str,
        email_body: str,
        scenarios: List[ReplyScenario]
    ) -> Tuple[Optional[ReplyScenario], float]:
        """התאמה באמצעות GPT"""
        
        # בניית רשימת תרחישים לפרומפט
        scenarios_list = []
        for s in scenarios:
            scenarios_list.append({
                "name": s.name,
                "display_name": s.display_name,
                "category": s.category,
                "description": s.keywords[:5] if s.keywords else []  # רק 5 מילות מפתח ראשונות
            })
        
        system_prompt = """אתה מנתח מיילים נכנסים ומתאים אותם לתרחישי תשובה מוגדרים מראש.

נתח את המייל הנכנס והחזר את התרחיש המתאים ביותר.

החזר תשובה ב-JSON בפורמט:
{
    "scenario_name": "שם התרחיש או null אם אין התאמה",
    "confidence": 0.0-1.0,
    "reasoning": "הסבר קצר למה בחרת בתרחיש זה"
}

תרחישים זמינים:
""" + json.dumps(scenarios_list, ensure_ascii=False, indent=2)

        user_prompt = f"""נושא המייל: {email_subject}

תוכן המייל:
{email_body[:1000]}"""  # מגבלת 1000 תווים
        
        response, _ = await self.openai.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=200
        )
        
        # פרסור התשובה
        result = json.loads(response)
        scenario_name = result.get("scenario_name")
        confidence = result.get("confidence", 0)
        
        if scenario_name:
            # מציאת התרחיש במסד
            for s in scenarios:
                if s.name == scenario_name:
                    return s, confidence
        
        return None, 0
    
    def _match_with_keywords(
        self,
        email_subject: str,
        email_body: str,
        scenarios: List[ReplyScenario]
    ) -> Tuple[Optional[ReplyScenario], float]:
        """התאמה באמצעות מילות מפתח"""
        
        # איחוד נושא ותוכן
        full_text = f"{email_subject} {email_body}".lower()
        
        best_match = None
        best_score = 0
        
        for scenario in scenarios:
            if not scenario.keywords:
                continue
            
            matches = 0
            for keyword in scenario.keywords:
                # בדיקה case-insensitive
                if keyword.lower() in full_text:
                    matches += 1
            
            if matches > 0:
                # חישוב ציון (יחס ההתאמה + בונוס לעדיפות)
                score = (matches / len(scenario.keywords)) * 0.8 + (scenario.priority / 200) * 0.2
                
                if score > best_score:
                    best_score = score
                    best_match = scenario
        
        if best_match:
            return best_match, min(best_score, 1.0)
        
        return None, 0
    
    def render_response(
        self,
        scenario: ReplyScenario,
        lead_name: str = None,
        lead_domain: str = None,
        calculators_link: str = "https://loan-israel.co.il/category/כלים-ומחשבונים/"
    ) -> Tuple[str, str]:
        """
        מרנדר את התשובה עם המשתנים
        
        Returns:
            Tuple of (subject, body)
        """
        variables = {
            "lead_name": lead_name or "שלום",
            "domain": lead_domain or "",
            "calculators_link": calculators_link,
            "sender_name": scenario.sender_name,
            "sender_title": scenario.sender_title,
        }
        
        subject = scenario.response_subject or ""
        body = scenario.response_body or ""
        
        # החלפת משתנים
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            subject = subject.replace(placeholder, value)
            body = body.replace(placeholder, value)
        
        return subject, body
    
    async def generate_gpt_response(
        self,
        scenario: ReplyScenario,
        trigger_message: str,
        trigger_subject: str = "",
        lead_name: str = None,
        lead_domain: str = None
    ) -> Tuple[str, str]:
        """
        מייצר תשובה מותאמת אישית באמצעות GPT
        
        Returns:
            Tuple of (subject, body)
        """
        # בניית הפרומפט
        gpt_prompt = """אתה אייל עובדיה, מנהל מקצועי בחברת "רק תבקש" - פלטפורמה ישראלית למחשבונים פיננסיים.

הלקוח שלח הודעה. עליך לנסח תשובה מקצועית ואישית.

פרטי הלקוח:
- שם: {lead_name}
- דומיין: {lead_domain}

נושא ההודעה: {trigger_subject}

תוכן ההודעה:
{trigger_message}

כללים לתשובה:
1. התייחס ספציפית לבקשה/שאלה שלו
2. אם מבקש משהו שאין לנו (כמו מחשבון פוריות) - הסבר בנימוס שאנחנו מתמחים במחשבונים פיננסיים (הלוואות, משכנתא, חיסכון, פנסיה)
3. תמיד הצע את המחשבונים הפיננסיים שלנו: https://loan-israel.co.il/category/כלים-ומחשבונים/
4. שמור על טון חברי ומקצועי
5. התשובה צריכה להיות קצרה וממוקדת

החזר תשובה ב-JSON בפורמט:
{{
    "subject": "נושא המייל",
    "body": "תוכן התשובה המלא כולל חתימה"
}}

חתום תמיד:
אייל עובדיה
מנהל מקצועי | רק תבקש"""

        formatted_prompt = gpt_prompt.format(
            lead_name=lead_name or "לקוח יקר",
            lead_domain=lead_domain or "לא צוין",
            trigger_subject=trigger_subject or "ללא נושא",
            trigger_message=trigger_message[:1500]  # מגבלת תווים
        )
        
        try:
            response, _ = await self.openai.generate(
                system_prompt="אתה עוזר שמייצר תשובות מקצועיות למיילים בעברית. החזר JSON בלבד.",
                user_prompt=formatted_prompt,
                temperature=0.7,
                max_tokens=500
            )
            
            # פרסור התשובה
            result = json.loads(response)
            subject = result.get("subject", "תשובה לפנייתך")
            body = result.get("body", "")
            
            logger.info(f"✅ GPT generated custom response with subject: {subject}")
            return subject, body
            
        except Exception as e:
            logger.error(f"Failed to generate GPT response: {e}")
            # Fallback בסיסי
            return "תודה על פנייתך", f"""שלום {lead_name or 'לקוח יקר'},

תודה על פנייתך!

אנחנו ב"רק תבקש" מתמחים במחשבונים פיננסיים - הלוואות, משכנתאות, חיסכון ופנסיה.

הנה הקישור למחשבונים שלנו:
https://loan-israel.co.il/category/כלים-ומחשבונים/

אם יש שאלות נוספות - אני כאן!

אייל עובדיה
מנהל מקצועי | רק תבקש"""


# ========== Helper Functions ==========

async def match_and_prepare_reply(
    db: Session,
    email_subject: str,
    email_body: str,
    lead_name: str = None,
    lead_domain: str = None
) -> Dict[str, Any]:
    """
    פונקציית עזר - מתאימה תרחיש ומכינה את התשובה
    
    Returns:
        Dictionary with:
        - matched: bool
        - scenario_name: str
        - scenario_category: str
        - requires_human: bool
        - confidence: float
        - method: str
        - response_subject: str (if matched)
        - response_body: str (if matched)
    """
    matcher = ScenarioMatcher(db)
    
    scenario, confidence, method = await matcher.match_scenario(
        email_subject, email_body, lead_domain
    )
    
    if not scenario:
        return {
            "matched": False,
            "scenario_name": None,
            "scenario_category": None,
            "requires_human": False,
            "confidence": 0,
            "method": method,
        }
    
    # אם זה תרחיש GPT fallback - ייצור תשובה מותאמת אישית
    if method == "gpt_fallback" or scenario.name == "gpt_fallback":
        subject, body = await matcher.generate_gpt_response(
            scenario,
            trigger_message=email_body,
            trigger_subject=email_subject,
            lead_name=lead_name,
            lead_domain=lead_domain
        )
    else:
        subject, body = matcher.render_response(
            scenario,
            lead_name=lead_name,
            lead_domain=lead_domain
        )
    
    return {
        "matched": True,
        "scenario_name": scenario.name,
        "scenario_display_name": scenario.display_name,
        "scenario_category": scenario.category,
        "requires_human": scenario.requires_human,
        "confidence": confidence,
        "method": method,
        "response_subject": subject,
        "response_body": body,
    }
