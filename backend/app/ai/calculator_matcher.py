"""
PartnerCalc OS - Calculator Matcher
התאמת מחשבון מתאים לאתר באמצעות AI
"""
import json
import re
from typing import Dict, Any, Optional, List
from loguru import logger

from app.ai.ollama_client import get_ollama_client
from app.ai.openai_client import get_openai_client


class CalculatorMatcher:
    """
    התאמת מחשבון לאתר באמצעות AI
    """
    
    # הגדרות
    MAX_CONTENT_FOR_DIRECT_MATCH = 1500  # אם יותר מזה - נסכם קודם
    SUMMARY_MAX_LENGTH = 500  # אורך מקסימלי לסיכום
    
    SUMMARIZE_PROMPT = """סכם את האתר הבא בקצרה (עד 3 משפטים).
התמקד ב: מה האתר מציע, קהל יעד, שירותים עיקריים.

תוכן האתר:
{content}

סיכום קצר:"""

    MATCH_PROMPT = """נתח את תוכן האתר והתאם עד 3 מחשבונים מהרשימה.

תוכן האתר לניתוח:
{site_content}

רשימת המחשבונים הזמינים:
{calculators_json}

הוראות חשובות:
1. קרא את תוכן האתר בעיון וזהה את התחום העסקי
2. בחר 1-3 מחשבונים שבאמת מתאימים לתוכן האתר
3. תן ציון התאמה אמיתי (0.0-1.0) לפי הרלוונטיות
4. אם אף מחשבון לא מתאים ב-80% או יותר - הצע מחשבון חדש ב-suggested_new_calc
5. כתוב סיבה ספציפית לכל התאמה שמסבירה למה המחשבון מתאים לאתר הזה

כללים לבחירה:
- אתר הלוואות/אשראי → מחשבון הלוואות (13), מחשבון ריבית אפקטיבית (6)
- אתר משכנתא → מחשבון משכנתא (20)
- אתר רכב/ליסינג → מחשבון ליסינג (15), מחשבון רכב (14)
- אתר פנסיה/פרישה → מחשבון פנסיה (17)
- אתר השקעות → מחשבון ריבית דריבית (5)

החזר JSON בפורמט הזה בלבד (ללא טקסט נוסף):
{{"matches": [{{"calc_id": NUMBER, "score": DECIMAL, "reason": "סיבה ספציפית"}}], "suggested_new_calc": "שם מחשבון חדש או null"}}"""

    def __init__(self):
        self.ollama = None
    
    async def _get_ollama(self):
        """Get Ollama client lazily"""
        if self.ollama is None:
            self.ollama = get_ollama_client()
        return self.ollama
    
    async def _summarize_content(self, content: str) -> str:
        """סיכום תוכן ארוך לתוכן קצר"""
        summarize_model = "gemma2:9b"
        try:
            ollama = await self._get_ollama()
            
            # קח רק 3000 תווים ראשונים לסיכום
            truncated = content[:3000]
            
            prompt = self.SUMMARIZE_PROMPT.format(content=truncated)
            
            logger.info(f"📝 Summarizing content ({len(content)} chars -> {len(truncated)} for summary)")
            
            # שימוש במודל קטן ומהיר לסיכום
            summary = await ollama.generate(
                system_prompt="סכם בקצרה בעברית.",
                user_prompt=prompt,
                model=summarize_model,
                temperature=0.3,
                max_tokens=3000
            )
            
            # 🔥 פנה זיכרון GPU אחרי הסיכום
            logger.info(f"❄️ Unloading {summarize_model} from GPU...")
            await ollama.unload_model(summarize_model)
            
            # נקה תגיות חשיבה
            summary = re.sub(r'<think>.*?</think>', '', summary, flags=re.DOTALL)
            summary = summary.strip()
            
            logger.info(f"✅ Summary: {summary[:100]}...")
            return summary[:self.SUMMARY_MAX_LENGTH]
            
        except Exception as e:
            logger.error(f"Error summarizing: {e}")
            # נסה לפנות זיכרון גם במקרה של שגיאה
            try:
                ollama = await self._get_ollama()
                await ollama.unload_model(summarize_model)
            except:
                pass
            # אם נכשל - החזר את ה-500 תווים ראשונים
            return content[:500]
    
    def _prepare_calculators_json(self, calculators: List[Dict]) -> str:
        """הכנת JSON של מחשבונים לפרומפט - כל המחשבונים"""
        calc_list = []
        for calc in calculators[:25]:  # עד 25 מחשבונים
            calc_list.append({
                "id": calc["id"],
                "name": calc["name"],
                "desc": (calc.get("ai_summary") or calc.get("intent_description", ""))[:100]
            })
        
        return json.dumps(calc_list, ensure_ascii=False)
    
    async def match_calculator(
        self,
        site_content: str,
        business_type: str,
        calculators: List[Dict]
    ) -> Dict[str, Any]:
        """
        התאמת מחשבון לאתר
        """
        content_length = len(site_content)
        logger.info(f"🧮 Matching calculator for {business_type} site ({content_length} chars)")
        
        try:
            ollama = await self._get_ollama()
            
            # 🔥 סיכום חכם - אם התוכן ארוך מדי
            if content_length > self.MAX_CONTENT_FOR_DIRECT_MATCH:
                logger.info(f"📝 Content too long ({content_length} > {self.MAX_CONTENT_FOR_DIRECT_MATCH}), summarizing first...")
                processed_content = await self._summarize_content(site_content)
            else:
                processed_content = site_content
            
            # הכן JSON מקוצר של מחשבונים
            calcs_json = self._prepare_calculators_json(calculators)
            
            # בנה prompt
            prompt = self.MATCH_PROMPT.format(
                site_content=processed_content,
                calculators_json=calcs_json
            )
            
            logger.info(f"📤 Sending to AI (prompt length: {len(prompt)} chars)")
            
            match_model = "hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M"
            
            # קריאה ל-AI - צריך הרבה טוקנים כי DictaLM-Thinking משתמש בטוקנים גם לחשיבה
            response = await ollama.generate(
                system_prompt="השב JSON בלבד. ללא הסברים.",
                user_prompt=prompt,
                model=match_model,
                temperature=0.2,
                max_tokens=4000
            )
            
            # 🔥 פנה זיכרון GPU אחרי ההתאמה
            logger.info(f"❄️ Unloading {match_model} from GPU...")
            await ollama.unload_model(match_model)
            
            logger.info(f"🤖 AI Response: {response[:300]}")
            
            # נקה תגיות חשיבה
            response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
            response = re.sub(r'<\|.*?\|>', '', response)
            
            # חלץ JSON
            json_match = self._extract_json(response)
            
            if json_match:
                try:
                    parsed = json.loads(json_match)
                    valid_ids = [c["id"] for c in calculators]
                    
                    # פורמט חדש - מספר מחשבונים
                    if "matches" in parsed:
                        matches = parsed.get("matches", [])
                        valid_matches = []
                        for m in matches:
                            calc_id = m.get("calc_id")
                            if calc_id in valid_ids:
                                valid_matches.append({
                                    "calc_id": calc_id,
                                    "score": float(m.get("score", 0.5)),
                                    "reason": m.get("reason", "")
                                })
                        
                        if valid_matches:
                            # המחשבון הראשון הוא העיקרי
                            primary = valid_matches[0]
                            return {
                                "calc_id": primary["calc_id"],
                                "calc_name": "",
                                "match_score": primary["score"],
                                "reasoning": primary["reason"],
                                "all_matches": valid_matches,  # כל ההתאמות
                                "suggested_new_calc": parsed.get("suggested_new_calc"),
                                "success": True
                            }
                    
                    # פורמט ישן - מחשבון אחד
                    calc_id = parsed.get("calc_id")
                    if calc_id not in valid_ids:
                        calc_id = valid_ids[0] if valid_ids else None
                    
                    return {
                        "calc_id": calc_id,
                        "calc_name": parsed.get("calc_name", ""),
                        "match_score": float(parsed.get("match_score", parsed.get("score", 0.5))),
                        "reasoning": parsed.get("reasoning", parsed.get("reason", "")),
                        "suggested_new_calc": parsed.get("suggested_new_calc"),
                        "success": True
                    }
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
            
            # Fallback
            logger.warning(f"Could not parse, using fallback. Response: {response[:200]}")
            return {
                "calc_id": calculators[0]["id"] if calculators else None,
                "calc_name": calculators[0]["name"] if calculators else "",
                "match_score": 0.3,
                "reasoning": "לא הצלחתי לנתח את האתר - בחרתי מחשבון כללי",
                "suggested_new_calc": None,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error matching calculator: {e}")
            # נסה לפנות זיכרון גם במקרה של שגיאה
            try:
                ollama = await self._get_ollama()
                await ollama.unload_model("hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M")
            except:
                pass
            return {
                "calc_id": None,
                "calc_name": "",
                "match_score": 0,
                "reasoning": str(e),
                "suggested_new_calc": None,
                "success": False
            }
    
    async def match_calculator_gpt(
        self,
        site_content: str,
        business_type: str,
        calculators: List[Dict]
    ) -> Dict[str, Any]:
        """
        התאמת מחשבון לאתר באמצעות OpenAI GPT
        משתמש ב-Ollama לסיכום, GPT להתאמה
        מחזיר גם זמן ביצוע!
        """
        content_length = len(site_content)
        logger.info(f"⚡ GPT Matching calculator for {business_type} site ({content_length} chars)")
        
        try:
            # 🔥 סיכום חכם עם Ollama (אותו תהליך כמו קודם)
            if content_length > self.MAX_CONTENT_FOR_DIRECT_MATCH:
                logger.info(f"📝 Content too long ({content_length} > {self.MAX_CONTENT_FOR_DIRECT_MATCH}), summarizing first...")
                processed_content = await self._summarize_content(site_content)
            else:
                processed_content = site_content
            
            # הכן JSON מקוצר של מחשבונים
            calcs_json = self._prepare_calculators_json(calculators)
            
            # בנה prompt
            prompt = self.MATCH_PROMPT.format(
                site_content=processed_content,
                calculators_json=calcs_json
            )
            
            logger.info(f"📤 Sending to GPT (prompt length: {len(prompt)} chars)")
            
            # קריאה ל-OpenAI GPT
            openai = get_openai_client()
            response, duration = await openai.generate(
                system_prompt="אתה מומחה להתאמת מחשבונים פיננסיים לאתרים. השב JSON בלבד.",
                user_prompt=prompt,
                model="gpt-4o-mini",
                temperature=0.2,
                max_tokens=1000
            )
            
            logger.info(f"⚡ GPT Response in {duration:.2f}s: {response[:300]}")
            
            # חלץ JSON (GPT מחזיר JSON נקי יותר)
            json_match = self._extract_json(response)
            
            if json_match:
                try:
                    parsed = json.loads(json_match)
                    valid_ids = [c["id"] for c in calculators]
                    
                    # פורמט חדש - מספר מחשבונים
                    if "matches" in parsed:
                        matches = parsed.get("matches", [])
                        valid_matches = []
                        for m in matches:
                            calc_id = m.get("calc_id")
                            if calc_id in valid_ids:
                                valid_matches.append({
                                    "calc_id": calc_id,
                                    "score": float(m.get("score", 0.5)),
                                    "reason": m.get("reason", "")
                                })
                        
                        if valid_matches:
                            primary = valid_matches[0]
                            return {
                                "calc_id": primary["calc_id"],
                                "calc_name": "",
                                "match_score": primary["score"],
                                "reasoning": primary["reason"],
                                "all_matches": valid_matches,
                                "suggested_new_calc": parsed.get("suggested_new_calc"),
                                "duration_seconds": duration,
                                "success": True
                            }
                    
                    # פורמט ישן
                    calc_id = parsed.get("calc_id")
                    if calc_id not in valid_ids:
                        calc_id = valid_ids[0] if valid_ids else None
                    
                    return {
                        "calc_id": calc_id,
                        "calc_name": parsed.get("calc_name", ""),
                        "match_score": float(parsed.get("match_score", parsed.get("score", 0.5))),
                        "reasoning": parsed.get("reasoning", parsed.get("reason", "")),
                        "suggested_new_calc": parsed.get("suggested_new_calc"),
                        "duration_seconds": duration,
                        "success": True
                    }
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"GPT JSON parse error: {e}")
            
            # Fallback
            logger.warning(f"GPT: Could not parse, using fallback. Response: {response[:200]}")
            return {
                "calc_id": calculators[0]["id"] if calculators else None,
                "calc_name": calculators[0]["name"] if calculators else "",
                "match_score": 0.3,
                "reasoning": "לא הצלחתי לנתח את האתר - בחרתי מחשבון כללי",
                "suggested_new_calc": None,
                "duration_seconds": duration,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in GPT matching: {e}")
            return {
                "calc_id": None,
                "calc_name": "",
                "match_score": 0,
                "reasoning": str(e),
                "suggested_new_calc": None,
                "duration_seconds": 0,
                "success": False
            }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """חילוץ JSON מתוך טקסט - עם ניקוי אגרסיבי"""
        # נקה שורות חדשות ורווחים מיותרים
        text = text.replace('\n', ' ').replace('\r', '')
        
        # מצא את ה-JSON
        start_idx = text.find('{')
        if start_idx == -1:
            logger.warning("No { found in response")
            return None
        
        brace_count = 0
        for i, char in enumerate(text[start_idx:], start_idx):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    potential_json = text[start_idx:i+1]
                    logger.info(f"🔍 Found JSON candidate: {potential_json[:200]}")
                    
                    # נסה לפרסר כמו שהוא
                    try:
                        json.loads(potential_json)
                        return potential_json
                    except:
                        pass
                    
                    # נסה לתקן JSON שבור - החלף null בעברית
                    fixed = potential_json.replace('null', 'null')
                    fixed = re.sub(r':\s*"([^"]*)"([^,}])', r': "\1"\2', fixed)
                    try:
                        json.loads(fixed)
                        return fixed
                    except:
                        pass
                    
                    # אם עדיין לא עובד, נסה regex פשוט
                    calc_id_match = re.search(r'"calc_id"\s*:\s*(\d+)', potential_json)
                    score_match = re.search(r'"match_score"\s*:\s*([\d.]+)', potential_json)
                    reason_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', potential_json)
                    
                    if calc_id_match:
                        # בנה JSON ידנית
                        manual_json = {
                            "calc_id": int(calc_id_match.group(1)),
                            "match_score": float(score_match.group(1)) if score_match else 0.7,
                            "reasoning": reason_match.group(1) if reason_match else "",
                            "suggested_new_calc": None
                        }
                        logger.info(f"🔧 Built manual JSON: {manual_json}")
                        return json.dumps(manual_json)
                    
                    break
        
        logger.warning(f"Could not extract valid JSON from: {text[:300]}")
        return None


# Singleton
_calculator_matcher: Optional[CalculatorMatcher] = None


def get_calculator_matcher() -> CalculatorMatcher:
    """קבלת instance של CalculatorMatcher"""
    global _calculator_matcher
    if _calculator_matcher is None:
        _calculator_matcher = CalculatorMatcher()
    return _calculator_matcher
