"""
PartnerCalc OS - Ollama Client
אינטגרציה עם Ollama API
"""
import httpx
import json
import time
from typing import Optional, Dict, Any
from loguru import logger

from app.config import settings


class OllamaClient:
    """
    Client לתקשורת עם Ollama API
    """
    
    def __init__(self, host: str = None, model: str = None):
        self.host = host or settings.ollama_host
        self.model = model or settings.ollama_model
        self.timeout = 120  # 2 דקות timeout
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        שליחת prompt ל-Ollama וקבלת תשובה
        
        Args:
            system_prompt: ההנחיות למודל
            user_prompt: השאלה/בקשה
            model: שם המודל (ברירת מחדל: dictalm)
            temperature: רמת היצירתיות (0-1)
            max_tokens: מקסימום טוקנים בתשובה
        
        Returns:
            התשובה מהמודל
        """
        model = model or self.model
        
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        logger.debug(f"Ollama request to {model}: {user_prompt[:100]}...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("response", "")
                
        except httpx.TimeoutException:
            logger.error(f"Ollama timeout after {self.timeout}s")
            raise Exception("Ollama timeout - המודל לקח יותר מדי זמן")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise Exception(f"Ollama HTTP error: {e.response.status_code}")
        
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def chat(
        self,
        messages: list,
        model: str = None,
        temperature: float = 0.7
    ) -> str:
        """
        שיחה עם המודל (מספר הודעות)
        
        Args:
            messages: רשימת הודעות [{"role": "user/assistant/system", "content": "..."}]
            model: שם המודל
            temperature: רמת היצירתיות
        
        Returns:
            התשובה מהמודל
        """
        model = model or self.model
        
        url = f"{self.host}/api/chat"
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                return result.get("message", {}).get("content", "")
                
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise
    
    async def is_available(self) -> bool:
        """
        בדיקה אם Ollama זמין
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.host}/api/tags")
                return response.status_code == 200
        except:
            return False
    
    async def list_models(self) -> list:
        """
        קבלת רשימת המודלים המותקנים
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.host}/api/tags")
                response.raise_for_status()
                
                result = response.json()
                return [m["name"] for m in result.get("models", [])]
                
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []
    
    async def load_model(self, model: str = None) -> dict:
        """
        טעינת מודל ל-GPU (שומר אותו חם בזיכרון)
        """
        model = model or self.model
        logger.info(f"🔥 Loading model to GPU: {model}")
        
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                # שליחת בקשה ריקה כדי לטעון את המודל
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": model,
                        "prompt": "",
                        "keep_alive": "24h"  # שמור טעון 24 שעות
                    }
                )
                response.raise_for_status()
                logger.info(f"✅ Model loaded to GPU: {model}")
                return {"status": "loaded", "model": model, "keep_alive": "24h"}
                
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    async def unload_model(self, model: str = None) -> dict:
        """
        הורדת מודל מה-GPU (משחרר זיכרון)
        """
        model = model or self.model
        logger.info(f"❄️ Unloading model from GPU: {model}")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": model,
                        "prompt": "",
                        "keep_alive": "0"  # הורד מיד
                    }
                )
                response.raise_for_status()
                logger.info(f"✅ Model unloaded from GPU: {model}")
                return {"status": "unloaded", "model": model}
                
        except Exception as e:
            logger.error(f"Failed to unload model: {e}")
            raise
    
    async def get_gpu_status(self) -> dict:
        """
        קבלת סטטוס GPU ומודלים טעונים
        """
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.host}/api/ps")
                response.raise_for_status()
                
                result = response.json()
                models = result.get("models", [])
                
                return {
                    "loaded_models": [m.get("name") for m in models],
                    "count": len(models),
                    "details": models
                }
                
        except Exception as e:
            logger.error(f"Failed to get GPU status: {e}")
            return {"loaded_models": [], "count": 0, "error": str(e)}


class OllamaClientWithPrompts(OllamaClient):
    """
    Client מורחב עם תמיכה בניהול פרומפטים מ-DB
    """
    
    def __init__(self, session=None, **kwargs):
        super().__init__(**kwargs)
        self.session = session
    
    async def execute_prompt(
        self,
        node_name: str,
        variables: Dict[str, Any],
        lead_id: int = None
    ) -> Dict[str, Any]:
        """
        הרצת פרומפט מה-DB עם החלפת משתנים
        
        Args:
            node_name: שם הצומת (is_real_business, match_calculator...)
            variables: משתנים להחלפה
            lead_id: ID של הליד (לשמירה בלוג)
        
        Returns:
            התשובה מפורסרת כ-dict
        """
        from sqlalchemy import select
        from app.models.prompt import Prompt, AILog
        
        # שליפת הפרומפט מה-DB
        result = await self.session.execute(
            select(Prompt).where(Prompt.node_name == node_name)
        )
        prompt_config = result.scalar_one_or_none()
        
        if not prompt_config:
            raise ValueError(f"Prompt '{node_name}' not found")
        
        if not prompt_config.is_active:
            raise ValueError(f"Prompt '{node_name}' is not active")
        
        # החלפת משתנים
        user_prompt = prompt_config.user_prompt_template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            user_prompt = user_prompt.replace(placeholder, str(value))
        
        # קריאה ל-Ollama
        start_time = time.time()
        
        try:
            response_text = await self.generate(
                system_prompt=prompt_config.system_prompt,
                user_prompt=user_prompt,
                model=prompt_config.model_name,
                temperature=prompt_config.temperature,
                max_tokens=prompt_config.max_tokens
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # ניסיון לפרסר JSON
            response_parsed = self._parse_json_response(response_text)
            success = True
            error_message = None
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            response_text = None
            response_parsed = None
            success = False
            error_message = str(e)
        
        # שמירה בלוג
        ai_log = AILog(
            prompt_id=prompt_config.id,
            lead_id=lead_id,
            input_data=variables,
            full_prompt=user_prompt,
            response=response_text,
            response_parsed=response_parsed,
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )
        
        self.session.add(ai_log)
        await self.session.flush()
        
        if not success:
            raise Exception(error_message)
        
        return response_parsed or {"raw_response": response_text}
    
    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """
        ניסיון לחלץ JSON מהתשובה
        """
        if not text:
            return None
        
        # נסה לפרסר ישירות
        try:
            return json.loads(text)
        except:
            pass
        
        # חפש JSON בתוך הטקסט
        import re
        json_pattern = r'\{[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except:
                continue
        
        # חפש JSON מורכב יותר
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except:
            pass
        
        return None


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """
    קבלת instance של Ollama client
    """
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
