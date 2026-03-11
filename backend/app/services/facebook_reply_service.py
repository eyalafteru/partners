"""
PartnerCalc OS - Facebook Reply Bot Service
שירות AI לניתוח תגובות ויצירת תשובות
"""
import os
import httpx
import re
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger

from app.config import settings
from app.services.post_generator_service import get_post_generator_service


# Prompt לניתוח תגובה
ANALYZE_REPLY_PROMPT = """נתח את התגובה הבאה מפייסבוק וזהה:
1. כוונת המגיב (intent)
2. האם מבקש לעבור לפרטי
3. רמת העניין

תגובה:
"{message}"

הקשר הפוסט:
{post_context}

החזר JSON בפורמט הבא בלבד (ללא הסברים):
{{
    "intent": "interested|question|private_request|spam|complaint|thanks|other",
    "wants_private": true|false,
    "interest_level": "high|medium|low|none",
    "suggested_channel": "comment|messenger",
    "key_points": ["נקודה 1", "נקודה 2"],
    "sentiment": "positive|neutral|negative"
}}"""

# Prompt ליצירת תשובה
GENERATE_RESPONSE_PROMPT = """אתה נציג שירות לקוחות מקצועי של חברת מחשבונים פיננסיים.
צור תשובה לתגובה הבאה בפייסבוק.

תגובת הלקוח:
"{message}"

ניתוח התגובה:
- כוונה: {intent}
- רמת עניין: {interest_level}
- ערוץ מומלץ: {channel}

היסטוריית השיחה (אם יש):
{conversation_history}

מידע על השירות שלנו:
- אנחנו מציעים מחשבונים פיננסיים להטמעה בחינם באתרים
- ההטמעה פשוטה - העתק הדבק
- אפשר להתאים צבעים לאתר
- יש מגוון מחשבונים: הלוואות, משכנתאות, חיסכון ועוד
- קישור: https://loan-israel.co.il/category/כלים-ומחשבונים/

דרישות לתשובה:
1. כתוב בעברית
2. היה ידידותי ומקצועי
3. אם הערוץ הוא "messenger" - יש להזמין לשיחה פרטית
4. אם הערוץ הוא "comment" - יש לענות בקצרה ובאופן מעודד
5. כלול קריאה לפעולה
6. אורך: 2-4 משפטים
7. חובה: כתוב בשפה ניטרלית מבחינת מגדר - מתאימה גם לנשים וגם לגברים.
   במקום פנייה בגוף שני (תוכל, תרצה, תמצא) - השתמש בצורות סביליות/ניטרליות.
   דוגמאות: "ניתן למצוא" במקום "תוכל למצוא", "אפשר לבדוק" במקום "תוכל לבדוק",
   "מוזמנים לפנות" במקום "מוזמן לפנות", "שווה לבדוק" במקום "תבדוק".

החזר רק את טקסט התשובה, ללא הסברים."""

# מילים שמזהות בקשה לפרטי
PRIVATE_REQUEST_KEYWORDS = [
    "בפרטי", "פרטי", "שלח לי", "תשלח לי", "בהודעה", 
    "במסנג'ר", "messenger", "dm", "private", "פרטית",
    "להתקשר", "טלפון", "וואטסאפ", "whatsapp"
]


class FacebookReplyBotService:
    """שירות AI לניתוח תגובות ויצירת תשובות"""
    
    def __init__(self):
        self.openai_api_key = (getattr(settings, 'openai_api_key', '') or '').strip()
        # טעינה מ-settings (מקובץ .env) או מ-os.environ כ-fallback
        _ak = (getattr(settings, 'anthropic_api_key', '') or '').strip().replace("\r", "").replace("\n", "")
        if not _ak:
            _ak = (os.environ.get("ANTHROPIC_API_KEY") or "").strip().replace("\r", "").replace("\n", "")
        self.anthropic_api_key = _ak
        if self.anthropic_api_key:
            logger.info("Anthropic API key: set (len={})", len(self.anthropic_api_key))
        else:
            logger.debug("Anthropic API key: not set")
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.openai_api_key) or bool(self.anthropic_api_key)
    
    async def _call_gpt(
        self,
        prompt: str,
        system_message: str = "You are a helpful assistant.",
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """קריאה ל-AI - משתמש באותה פנייה כמו ביצירת פוסטים (Claude) או OpenAI"""
        if not self.is_configured:
            logger.error("No AI API key configured (neither OpenAI nor Anthropic)")
            return None
        
        # כשמוגדר Anthropic – אותה פניית API כמו ב"צור פוסטים": אותו מודל, אותו _call_ai, רק הפרומט שונה
        if self.anthropic_api_key:
            post_gen = get_post_generator_service()
            if post_gen.anthropic_api_key:
                model = post_gen._get_available_model()  # כמו ביצירת פוסטים: claude-sonnet-4
                return await post_gen._call_ai(
                    prompt=prompt,
                    system_message=system_message,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            return await self._call_claude(prompt, system_message, temperature, max_tokens)
        
        return await self._call_openai(prompt, system_message, model, temperature, max_tokens)
    
    async def _call_claude(
        self,
        prompt: str,
        system_message: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """קריאה ל-Anthropic Claude"""
        url = "https://api.anthropic.com/v1/messages"
        api_key = self.anthropic_api_key.strip()
        if not api_key:
            logger.error("ANTHROPIC_API_KEY is empty after strip")
            raise ValueError("מפתח Anthropic ריק. בדוק ANTHROPIC_API_KEY ב-.env")
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "claude-sonnet-4-5-20250514",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_message,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                # On 401, retry once with Authorization: Bearer (some envs expect it)
                if response.status_code == 401:
                    headers_bearer = {
                        "Authorization": f"Bearer {api_key}",
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    }
                    response = await client.post(url, json=payload, headers=headers_bearer)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("content") or []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "").strip()
                            if text:
                                return text
                    if content and isinstance(content[0], dict) and "text" in content[0]:
                        return (content[0].get("text") or "").strip()
                    logger.warning("Claude API: no text block in content")
                    return None
                else:
                    err_text = response.text
                    try:
                        err_body = response.json()
                        err_text = err_body.get("error", {}).get("message", err_text) if isinstance(err_body.get("error"), dict) else err_text
                    except Exception:
                        pass
                    logger.error(f"Claude API error: {response.status_code} - {err_text}")
                    raise ValueError(f"שגיאת Claude API ({response.status_code}): {err_text[:200]}")
                    
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Claude call error: {e}")
            raise ValueError(f"שגיאת חיבור ל-AI: {e!s}") from e
    
    async def _call_openai(
        self,
        prompt: str,
        system_message: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> Optional[str]:
        """קריאה ל-OpenAI GPT"""
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"].strip()
                else:
                    logger.error(f"GPT API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"GPT call error: {e}")
            return None
    
    def check_keywords_for_private(self, message: str) -> bool:
        """
        בדיקה מהירה אם ההודעה מכילה בקשה לפרטי
        """
        message_lower = message.lower()
        
        for keyword in PRIVATE_REQUEST_KEYWORDS:
            if keyword in message_lower:
                return True
        
        return False
    
    async def analyze_reply(
        self,
        message: str,
        post_context: str = ""
    ) -> Dict[str, Any]:
        """
        ניתוח תגובה וזיהוי כוונה
        
        Args:
            message: תוכן התגובה
            post_context: הקשר הפוסט המקורי
            
        Returns:
            dict עם ניתוח התגובה
        """
        # ברירת מחדל
        result = {
            "intent": "other",
            "wants_private": False,
            "interest_level": "medium",
            "suggested_channel": "comment",
            "key_points": [],
            "sentiment": "neutral",
            "analysis_method": "default"
        }
        
        # בדיקה מהירה למילות מפתח
        if self.check_keywords_for_private(message):
            result["wants_private"] = True
            result["suggested_channel"] = "messenger"
            result["intent"] = "private_request"
        
        # ניתוח מעמיק עם GPT
        prompt = ANALYZE_REPLY_PROMPT.format(
            message=message,
            post_context=post_context or "פוסט על מחשבונים להטמעה בחינם"
        )
        
        gpt_result = await self._call_gpt(
            prompt=prompt,
            system_message="אתה מומחה בניתוח תקשורת ושירות לקוחות. החזר תמיד JSON תקין.",
            temperature=0.3
        )
        
        if gpt_result:
            try:
                # ניקוי JSON
                json_str = gpt_result.strip()
                if json_str.startswith("```"):
                    json_str = json_str.split("```")[1]
                    if json_str.startswith("json"):
                        json_str = json_str[4:]
                
                import json
                parsed = json.loads(json_str)
                
                result.update(parsed)
                result["analysis_method"] = "gpt"
                
                logger.info(f"🤖 ✅ Reply analyzed: intent={result['intent']}, wants_private={result['wants_private']}")
                
            except Exception as e:
                logger.warning(f"🤖 ⚠️ Failed to parse GPT analysis: {e}")
                result["analysis_method"] = "keyword_fallback"
        
        return result
    
    async def generate_response(
        self,
        message: str,
        intent: str = "other",
        interest_level: str = "medium",
        channel: str = "comment",
        conversation_history: List[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        יצירת תשובה לתגובה
        
        Args:
            message: תוכן התגובה
            intent: כוונת המגיב
            interest_level: רמת העניין
            channel: ערוץ התשובה
            conversation_history: היסטוריית השיחה
            
        Returns:
            טקסט התשובה
        """
        # הכנת היסטוריית שיחה
        history_text = "אין היסטוריה קודמת"
        if conversation_history and len(conversation_history) > 0:
            history_parts = []
            for msg in conversation_history[-5:]:  # 5 הודעות אחרונות
                direction = "לקוח" if msg.get("direction") == "inbound" else "אנחנו"
                history_parts.append(f"{direction}: {msg.get('content', '')[:100]}")
            history_text = "\n".join(history_parts)
        
        prompt = GENERATE_RESPONSE_PROMPT.format(
            message=message,
            intent=intent,
            interest_level=interest_level,
            channel=channel,
            conversation_history=history_text
        )
        
        response = await self._call_gpt(
            prompt=prompt,
            system_message="אתה נציג שירות לקוחות מקצועי וידידותי. ענה בעברית בשפה ניטרלית מבחינת מגדר - מתאימה לנשים ולגברים כאחד.",
            temperature=0.7
        )
        
        if response:
            logger.info(f"💬 ✅ Response generated for channel: {channel}")
        
        return response
    
    async def process_reply(
        self,
        message: str,
        post_context: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        עיבוד מלא של תגובה: ניתוח + יצירת תשובה
        
        Returns:
            dict עם analysis, suggested_response, suggested_channel
        """
        # ניתוח התגובה
        analysis = await self.analyze_reply(
            message=message,
            post_context=post_context
        )
        
        # יצירת תשובה
        response = await self.generate_response(
            message=message,
            intent=analysis.get("intent", "other"),
            interest_level=analysis.get("interest_level", "medium"),
            channel=analysis.get("suggested_channel", "comment"),
            conversation_history=conversation_history
        )
        
        return {
            "analysis": analysis,
            "suggested_response": response,
            "suggested_channel": analysis.get("suggested_channel", "comment"),
            "wants_private": analysis.get("wants_private", False)
        }
    
    def should_escalate_to_human(self, analysis: Dict[str, Any]) -> bool:
        """
        בדיקה אם צריך העברה לטיפול אנושי
        """
        escalation_intents = ["complaint", "urgent", "legal"]
        negative_sentiment = analysis.get("sentiment") == "negative"
        
        if analysis.get("intent") in escalation_intents:
            return True
        
        if negative_sentiment and analysis.get("interest_level") == "high":
            return True
        
        return False


# Singleton
_reply_service: Optional[FacebookReplyBotService] = None


def get_facebook_reply_service() -> FacebookReplyBotService:
    """קבלת instance של Facebook Reply Bot Service"""
    global _reply_service
    if _reply_service is None:
        _reply_service = FacebookReplyBotService()
    return _reply_service
