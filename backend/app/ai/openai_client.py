"""
PartnerCalc OS - OpenAI Client
אינטגרציה עם OpenAI GPT API
"""
import time
from typing import Optional, Dict, Any, Tuple
from openai import AsyncOpenAI
from loguru import logger

from app.config import settings


class OpenAIClient:
    """
    Client לתקשורת עם OpenAI API
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.client = AsyncOpenAI(api_key=self.api_key)
        self.default_model = "gpt-4o-mini"
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Tuple[str, float]:
        """
        שליחת prompt ל-OpenAI וקבלת תשובה עם מדידת זמן
        
        Args:
            system_prompt: ההנחיות למודל
            user_prompt: השאלה/בקשה
            model: שם המודל (ברירת מחדל: gpt-4o-mini)
            temperature: רמת היצירתיות (0-1)
            max_tokens: מקסימום טוקנים בתשובה
        
        Returns:
            Tuple of (response_text, duration_seconds)
        """
        model = model or self.default_model
        
        start_time = time.time()
        
        try:
            logger.info(f"🤖 Calling OpenAI {model}...")
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            duration = time.time() - start_time
            
            result = response.choices[0].message.content
            
            # Log usage stats
            usage = response.usage
            logger.info(
                f"✅ OpenAI response in {duration:.2f}s | "
                f"Tokens: {usage.prompt_tokens} in, {usage.completion_tokens} out"
            )
            
            return result, duration
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ OpenAI error after {duration:.2f}s: {e}")
            raise


# Singleton instance
_openai_client: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """קבלת instance של OpenAI Client"""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAIClient()
    return _openai_client
