"""
PartnerCalc OS - Calculator Scraper
סריקת עמודי המחשבונים ויצירת תקצירים באמצעות AI
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from loguru import logger

from app.scraper.smart_scraper import get_smart_scraper
from app.ai.ollama_client import get_ollama_client
from app.config import settings


class CalculatorScraper:
    """
    סורק עמודי מחשבונים ומייצר תקצירים באמצעות AI
    """
    
    SUMMARY_PROMPT = """אתה כותב תוכן שיווקי בעברית בלבד.

תוכן עמוד המחשבון:
{content}

כתוב תקציר קצר (2-3 משפטים בלבד) בעברית שמסביר:
- מה המחשבון מחשב
- למי הוא מתאים
- למה כדאי להטמיע אותו

🚨 חשוב מאוד:
- כתוב רק בעברית!
- התקציר חייב להיות קצר (עד 150 מילים)
- רשום עד 3 קהלי יעד
- רשום עד 3 יתרונות קצרים

השב בפורמט JSON בלבד (ללא טקסט נוסף):
{{"summary": "תקציר קצר בעברית", "target_audience": ["קהל 1", "קהל 2"], "benefits": ["יתרון 1", "יתרון 2"]}}"""

    def __init__(self):
        self.scraper = get_smart_scraper()
        self.ollama = None
    
    async def _get_ollama(self):
        """Get Ollama client lazily"""
        if self.ollama is None:
            self.ollama = get_ollama_client()
        return self.ollama
    
    async def scrape_calculator(self, url: str) -> Dict[str, Any]:
        """
        סריקת עמוד מחשבון בודד
        
        Returns:
            {
                "content": "תוכן העמוד",
                "title": "כותרת",
                "success": True/False,
                "error": None or "הודעת שגיאה"
            }
        """
        logger.info(f"🔍 Scraping calculator page: {url}")
        
        try:
            result = await self.scraper.scrape(url)
            
            if not result or result.get("error"):
                return {
                    "content": "",
                    "title": "",
                    "success": False,
                    "error": result.get("error", "Failed to scrape")
                }
            
            inner_text = result.get("inner_text", "")
            html = result.get("html", "")
            
            logger.info(f"📄 Scrape result - HTML length: {len(html)}, Text length: {len(inner_text)}")
            logger.info(f"📝 First 300 chars of text: {inner_text[:300]}")
            
            if not inner_text or len(inner_text) < 50:
                logger.warning(f"⚠️ Very little content scraped from {url} - only {len(inner_text)} chars")
                logger.warning(f"📄 HTML preview: {html[:500]}")
            
            return {
                "content": inner_text[:10000],
                "title": result.get("title", ""),
                "html": html[:30000],
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "content": "",
                "title": "",
                "success": False,
                "error": str(e)
            }
    
    async def generate_summary(self, content: str, calc_name: str) -> Dict[str, Any]:
        """
        יצירת תקציר AI למחשבון
        
        Returns:
            {
                "summary": "תקציר",
                "target_audience": ["קהל יעד"],
                "benefits": ["יתרונות"],
                "success": True/False
            }
        """
        logger.info(f"🤖 Generating AI summary for: {calc_name}")
        
        try:
            ollama = await self._get_ollama()
            
            # Truncate content if too long
            truncated_content = content[:5000] if len(content) > 5000 else content
            
            prompt = self.SUMMARY_PROMPT.format(content=truncated_content)
            
            response_text = await ollama.generate(
                system_prompt="אתה כותב תוכן שיווקי בעברית. השב תמיד ב-JSON תקין בלבד.",
                user_prompt=prompt,
                max_tokens=4000
            )
            
            # Parse JSON response
            import json
            import re
            
            logger.debug(f"AI Response: {response_text[:500]}...")
            
            # Find JSON in response
            json_match = re.search(r'\{[\s\S]*?\}', response_text)
            if json_match:
                try:
                    json_text = json_match.group()
                    # Clean up common issues
                    json_text = json_text.replace('\n', ' ').replace('\r', '')
                    parsed = json.loads(json_text)
                    
                    summary = parsed.get("summary", "")
                    # Clean summary - remove JSON artifacts
                    if isinstance(summary, str):
                        summary = summary.strip()
                    
                    logger.info(f"✅ Parsed summary: {summary[:100]}...")
                    
                    return {
                        "summary": summary,
                        "target_audience": parsed.get("target_audience", []),
                        "benefits": parsed.get("benefits", []),
                        "success": True
                    }
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
            
            # Fallback - extract text without JSON
            clean_text = re.sub(r'[{}\[\]":]', '', response_text)
            clean_text = ' '.join(clean_text.split())[:400]
            
            return {
                "summary": clean_text if clean_text else "תקציר לא זמין",
                "target_audience": [],
                "benefits": [],
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error generating summary for {calc_name}: {e}")
            return {
                "summary": "",
                "target_audience": [],
                "benefits": [],
                "success": False,
                "error": str(e)
            }
    
    async def scrape_and_summarize(self, calc_id: int, url: str, name: str) -> Dict[str, Any]:
        """
        סריקה מלאה של מחשבון - סריקת העמוד + יצירת תקציר
        
        Returns:
            {
                "calc_id": 1,
                "scraped_content": "תוכן",
                "ai_summary": "תקציר",
                "target_audience": [],
                "benefits": [],
                "scraped_at": datetime,
                "success": True/False
            }
        """
        logger.info(f"📊 Processing calculator {calc_id}: {name}")
        
        # Step 1: Scrape the page
        scrape_result = await self.scrape_calculator(url)
        
        if not scrape_result["success"]:
            return {
                "calc_id": calc_id,
                "scraped_content": "",
                "ai_summary": "",
                "target_audience": [],
                "benefits": [],
                "scraped_at": datetime.utcnow(),
                "success": False,
                "error": scrape_result.get("error")
            }
        
        # Step 2: Generate AI summary
        summary_result = await self.generate_summary(
            scrape_result["content"],
            name
        )
        
        return {
            "calc_id": calc_id,
            "scraped_content": scrape_result["content"],
            "ai_summary": summary_result.get("summary", ""),
            "target_audience": summary_result.get("target_audience", []),
            "benefits": summary_result.get("benefits", []),
            "scraped_at": datetime.utcnow(),
            "success": True
        }


# Singleton
_calculator_scraper: Optional[CalculatorScraper] = None


def get_calculator_scraper() -> CalculatorScraper:
    """קבלת instance של CalculatorScraper"""
    global _calculator_scraper
    if _calculator_scraper is None:
        _calculator_scraper = CalculatorScraper()
    return _calculator_scraper

