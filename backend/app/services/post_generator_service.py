"""
PartnerCalc OS - Post Generator Service
שירות ליצירת פוסטים ו-prompts לתמונות עם GPT
"""
import httpx
import random
from typing import Optional, Dict, Any, List
from loguru import logger

from app.config import settings
from app.services.replicate_service import get_replicate_service


# Prompt ליצירת וריאציה של פוסט
POST_VARIATION_PROMPT = """אתה מומחה שיווק דיגיטלי שכותב פוסטים לקבוצות פייסבוק של בעלי אתרים ועסקים.

🎯 המטרה: לגרום לבעלי אתרים להיכנס לאתר שלנו, לבחור מחשבון פיננסי חינמי ולהטמיע אותו באתר שלהם.

📌 מה אנחנו מציעים:
- מחשבונים פיננסיים חכמים (הלוואות, משכנתאות, חסכון, פנסיה ועוד)
- הטמעה בחינם לחלוטין
- קוד פשוט להעתקה והדבקה
- התאמת צבעים לעיצוב האתר בלחיצת כפתור
- ערך אמיתי לגולשים של האתר

שם הקבוצה: {group_name}
קהל יעד: {target_audience}
תבנית בסיס (אם יש): {base_template}

דרישות לפוסט:
1. כתוב בעברית, בטון ידידותי ומקצועי
2. אורך: 4-7 שורות
3. הדגש שזה בחינם וקל להטמעה
4. הסבר את הערך לבעל האתר ולגולשים שלו
5. כלול קריאה לפעולה - להיכנס לאתר ולבחור מחשבון
6. השתמש ב-2-3 אימוג'ים רלוונטיים (לא יותר מדי)
7. אל תהיה "מכירתי" מדי - תן ערך אמיתי
8. התאם לסוג הקבוצה (עסקים, שיווק, אתרים, נדל"ן וכו')

פוסטים קודמים (להימנע מחזרות):
{previous_posts}

הנחיות נוספות:
{additional_instructions}

🔗 הקישור לאתר: https://loan-israel.co.il/category/כלים-ומחשבונים/

החזר רק את טקסט הפוסט, ללא הסברים."""

# Prompt ליצירת prompt לתמונה
IMAGE_PROMPT_GENERATOR = """Create an image generation prompt for FLUX AI model.

Context: This is for a Facebook post offering FREE financial calculators that website owners can embed on their sites. The calculators help visitors make financial decisions (loans, mortgages, savings, etc.)

Facebook Post (in Hebrew):
{post_content}

Topic: {topic}

Requirements for the image:
1. Write the prompt in English only
2. Show a professional business/tech scene relevant to websites and finance
3. Ideas: laptop with calculator on screen, business person looking at financial charts, modern office with digital tools, website mockup with calculator widget
4. Style: Clean, modern, professional, corporate
5. Lighting: Bright, optimistic
6. NO text, words, or numbers visible
7. NO logos or brand names
8. Colors: Blues, greens (trust colors), white backgrounds
9. End with: "4k quality, professional marketing photo, clean composition"

Format: Single paragraph, 50-80 words.

Return ONLY the image prompt."""


class PostGeneratorService:
    """שירות יצירת פוסטים עם GPT/Claude"""
    
    def __init__(self):
        self.openai_api_key = settings.openai_api_key
        self.anthropic_api_key = getattr(settings, 'anthropic_api_key', '')
        self.default_model = getattr(settings, 'default_ai_model', 'gpt-4o-mini')
        self.replicate_service = get_replicate_service()
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.openai_api_key) or bool(self.anthropic_api_key)
    
    def get_available_models(self) -> List[Dict[str, str]]:
        """רשימת מודלים זמינים"""
        models = []
        if self.openai_api_key:
            models.extend([
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini (מהיר וזול)"},
                {"id": "gpt-4o", "name": "GPT-4o (איכותי)"},
            ])
        if self.anthropic_api_key:
            models.extend([
                {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"},
                {"id": "claude-sonnet-4-5", "name": "Claude Sonnet 4.5 (הכי חדש)"},
            ])
        return models
    
    async def _call_ai(
        self,
        prompt: str,
        system_message: str = "You are a helpful marketing assistant.",
        model: str = None,
        temperature: float = 0.8,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        קריאה ל-AI (GPT או Claude)
        """
        if not self.is_configured:
            logger.error("No AI API key configured")
            return None
        
        # בחירת מודל ברירת מחדל
        if model is None:
            model = self.default_model
        
        # Claude models
        if model.startswith("claude"):
            return await self._call_claude(prompt, system_message, model, temperature, max_tokens)
        # OpenAI models
        else:
            return await self._call_openai(prompt, system_message, model, temperature, max_tokens)
    
    async def _call_openai(
        self,
        prompt: str,
        system_message: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """קריאה ל-OpenAI GPT"""
        if not self.openai_api_key:
            logger.error("OpenAI API key not configured")
            return None
        
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
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"OpenAI call error: {e}")
            return None
    
    async def _call_claude(
        self,
        prompt: str,
        system_message: str,
        model: str,
        temperature: float,
        max_tokens: int
    ) -> Optional[str]:
        """קריאה ל-Anthropic Claude"""
        if not self.anthropic_api_key:
            logger.error("Anthropic API key not configured")
            return None
        
        # Map friendly names to API model names
        model_map = {
            "claude-sonnet-4": "claude-sonnet-4-20250514",
            "claude-sonnet-4-5": "claude-sonnet-4-5-20250514",
        }
        api_model = model_map.get(model, model)
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": api_model,
            "max_tokens": max_tokens,
            "system": system_message,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return data["content"][0]["text"].strip()
                else:
                    logger.error(f"Claude API error: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Claude call error: {e}")
            return None
    
    # Backward compatibility
    async def _call_gpt(self, *args, **kwargs) -> Optional[str]:
        return await self._call_ai(*args, **kwargs)
    
    async def generate_post_variation(
        self,
        topic: str,
        group_name: str,
        target_audience: str = "",
        base_template: str = "",
        previous_posts: List[str] = None,
        additional_instructions: str = "",
        model: str = None
    ) -> Optional[str]:
        """
        יצירת וריאציה ייחודית של פוסט
        
        Args:
            topic: נושא הפוסט
            group_name: שם הקבוצה
            target_audience: קהל היעד
            base_template: תבנית בסיס (אופציונלי)
            previous_posts: פוסטים קודמים להימנע מחזרות
            additional_instructions: הנחיות נוספות
            
        Returns:
            טקסט הפוסט, או None בשגיאה
        """
        # הכנת רשימת פוסטים קודמים
        prev_posts_text = "אין"
        if previous_posts and len(previous_posts) > 0:
            # מציג את 3 האחרונים
            recent = previous_posts[-3:]
            prev_posts_text = "\n".join([f"- {p[:100]}..." for p in recent])
        
        prompt = POST_VARIATION_PROMPT.format(
            topic=topic,
            group_name=group_name,
            target_audience=target_audience or "כללי",
            base_template=base_template or "אין - צור מאפס",
            previous_posts=prev_posts_text,
            additional_instructions=additional_instructions or "אין"
        )
        
        result = await self._call_ai(
            prompt=prompt,
            system_message="אתה מומחה שיווק דיגיטלי לעסקים B2B. אתה כותב פוסטים לקבוצות פייסבוק של בעלי אתרים, יזמים ומשווקים. המטרה שלך היא לגרום להם להטמיע מחשבונים פיננסיים חינמיים באתר שלהם. אתה כותב בעברית, בטון מקצועי אבל נגיש.",
            model=model,
            temperature=0.85
        )
        
        if result:
            logger.info(f"📝 ✅ Post generated for group: {group_name}")
        
        return result
    
    async def generate_image_prompt(
        self,
        post_content: str,
        topic: str = ""
    ) -> Optional[str]:
        """
        יצירת prompt לתמונה על בסיס הפוסט
        
        Args:
            post_content: תוכן הפוסט (עברית)
            topic: נושא הפוסט
            
        Returns:
            prompt לתמונה (אנגלית), או None בשגיאה
        """
        prompt = IMAGE_PROMPT_GENERATOR.format(
            post_content=post_content,
            topic=topic or "general marketing"
        )
        
        result = await self._call_gpt(
            prompt=prompt,
            system_message="You are an expert at creating image prompts for AI image generators.",
            temperature=0.7
        )
        
        if result:
            logger.info(f"🎨 ✅ Image prompt generated")
        
        return result
    
    async def generate_full_post(
        self,
        topic: str,
        group_name: str,
        include_image: bool = True,
        target_audience: str = "",
        base_template: str = "",
        previous_posts: List[str] = None,
        additional_instructions: str = ""
    ) -> Dict[str, Any]:
        """
        יצירת פוסט מלא עם/בלי תמונה
        
        Args:
            topic: נושא הפוסט
            group_name: שם הקבוצה
            include_image: האם לכלול תמונה
            target_audience: קהל היעד
            base_template: תבנית בסיס
            previous_posts: פוסטים קודמים
            additional_instructions: הנחיות נוספות
            
        Returns:
            dict עם content, image_url, image_prompt
        """
        result = {
            "content": None,
            "has_image": False,
            "image_prompt": None,
            "image_url": None,
            "error": None
        }
        
        # שלב 1: יצירת טקסט הפוסט
        post_content = await self.generate_post_variation(
            topic=topic,
            group_name=group_name,
            target_audience=target_audience,
            base_template=base_template,
            previous_posts=previous_posts,
            additional_instructions=additional_instructions
        )
        
        if not post_content:
            result["error"] = "Failed to generate post content"
            return result
        
        result["content"] = post_content
        
        # שלב 2: יצירת תמונה (אם נדרש)
        if include_image:
            # יצירת prompt לתמונה
            image_prompt = await self.generate_image_prompt(
                post_content=post_content,
                topic=topic
            )
            
            if image_prompt:
                result["image_prompt"] = image_prompt
                
                # יצירת התמונה עצמה
                image_url = await self.replicate_service.generate_post_image(
                    image_prompt=image_prompt
                )
                
                if image_url:
                    result["has_image"] = True
                    result["image_url"] = image_url
                    logger.info(f"📸 ✅ Full post with image generated for: {group_name}")
                else:
                    logger.warning(f"📸 ⚠️ Image generation failed, post will be without image")
            else:
                logger.warning(f"🎨 ⚠️ Image prompt generation failed")
        else:
            logger.info(f"📝 ✅ Post generated (no image) for: {group_name}")
        
        return result
    
    async def generate_campaign_posts(
        self,
        topic: str,
        groups: List[Dict[str, Any]],
        image_percentage: int = 50,
        base_template: str = "",
        target_audience: str = ""
    ) -> List[Dict[str, Any]]:
        """
        יצירת פוסטים לכל הקבוצות בקמפיין
        
        Args:
            topic: נושא הקמפיין
            groups: רשימת קבוצות (dict עם id, name)
            image_percentage: אחוז פוסטים עם תמונה
            base_template: תבנית בסיס
            target_audience: קהל יעד
            
        Returns:
            רשימת פוסטים שנוצרו
        """
        posts = []
        previous_posts = []
        
        for i, group in enumerate(groups):
            # החלטה אם לכלול תמונה
            include_image = random.randint(1, 100) <= image_percentage
            
            logger.info(f"📝 Generating post {i+1}/{len(groups)} for {group.get('name')}...")
            
            post = await self.generate_full_post(
                topic=topic,
                group_name=group.get("name", ""),
                include_image=include_image,
                target_audience=target_audience,
                base_template=base_template,
                previous_posts=previous_posts
            )
            
            post["group_id"] = group.get("id")
            post["group_name"] = group.get("name")
            posts.append(post)
            
            # שמירת הפוסט לרשימת הקודמים
            if post.get("content"):
                previous_posts.append(post["content"])
        
        logger.info(f"📦 Generated {len(posts)} posts for campaign")
        return posts


# Singleton
_post_generator: Optional[PostGeneratorService] = None


def get_post_generator_service() -> PostGeneratorService:
    """קבלת instance של Post Generator Service"""
    global _post_generator
    if _post_generator is None:
        _post_generator = PostGeneratorService()
    return _post_generator
