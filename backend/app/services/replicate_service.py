"""
PartnerCalc OS - Replicate Image Generation Service
שירות ליצירת תמונות עם FLUX דרך Replicate API
"""
import httpx
import asyncio
from typing import Optional, Dict, Any
from loguru import logger

from app.config import settings


class ReplicateImageService:
    """שירות יצירת תמונות עם Replicate FLUX"""
    
    def __init__(self):
        self.api_token = settings.replicate_api_token
        self.flux_version = settings.replicate_flux_version
        self.base_url = "https://api.replicate.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    @property
    def is_configured(self) -> bool:
        """בדיקה אם השירות מוגדר"""
        return bool(self.api_token)
    
    async def create_prediction(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        output_format: str = "png",
        num_outputs: int = 1,
        num_inference_steps: int = 42,
        guidance_scale: float = 3.4,
        prompt_strength: float = 0.8,
        lora_scale: float = 0.8,
        hf_lora: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        יצירת prediction חדש ב-Replicate
        
        Args:
            prompt: תיאור התמונה הרצויה (אנגלית)
            aspect_ratio: יחס גובה-רוחב (1:1, 16:9, 9:16, etc.)
            output_format: פורמט הפלט (png, jpg, webp)
            num_outputs: כמות תמונות
            num_inference_steps: צעדי inference (איכות)
            guidance_scale: עוצמת ההנחיה
            prompt_strength: עוצמת ה-prompt
            lora_scale: עוצמת ה-LoRA
            hf_lora: מודל LoRA מ-HuggingFace (אופציונלי)
            
        Returns:
            dict עם prediction_id ו-status, או None בשגיאה
        """
        if not self.is_configured:
            logger.warning("🖼️ Replicate not configured - skipping image generation")
            return None
        
        try:
            url = f"{self.base_url}/predictions"
            
            input_data = {
                "prompt": prompt,
                "output_format": output_format,
                "num_outputs": num_outputs,
                "aspect_ratio": aspect_ratio,
                "num_inference_steps": num_inference_steps,
                "guidance_scale": guidance_scale,
                "prompt_strength": prompt_strength,
                "lora_scale": lora_scale,
                "output_quality": 100
            }
            
            # הוספת LoRA אם סופק
            if hf_lora:
                input_data["hf_lora"] = hf_lora
            
            payload = {
                "version": self.flux_version,
                "input": input_data
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                
                if response.status_code in [200, 201]:
                    data = response.json()
                    logger.info(f"🖼️ ✅ Prediction created: {data.get('id')}")
                    return {
                        "prediction_id": data.get("id"),
                        "status": data.get("status"),
                        "urls": data.get("urls", {})
                    }
                else:
                    logger.error(f"🖼️ ❌ Prediction failed: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"🖼️ ❌ Replicate error: {e}")
            return None
    
    async def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """
        קבלת סטטוס ותוצאות של prediction
        
        Args:
            prediction_id: מזהה ה-prediction
            
        Returns:
            dict עם סטטוס ותוצאות, או None בשגיאה
        """
        if not self.is_configured:
            return None
        
        try:
            url = f"{self.base_url}/predictions/{prediction_id}"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=self.headers)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "id": data.get("id"),
                        "status": data.get("status"),
                        "output": data.get("output"),
                        "error": data.get("error"),
                        "metrics": data.get("metrics")
                    }
                else:
                    logger.error(f"🖼️ ❌ Get prediction failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"🖼️ ❌ Get prediction error: {e}")
            return None
    
    async def wait_for_result(
        self,
        prediction_id: str,
        max_wait_seconds: int = 120,
        poll_interval: float = 2.0
    ) -> Optional[str]:
        """
        המתנה לתוצאת ה-prediction
        
        Args:
            prediction_id: מזהה ה-prediction
            max_wait_seconds: זמן המתנה מקסימלי
            poll_interval: מרווח בין בדיקות
            
        Returns:
            URL של התמונה, או None בשגיאה/timeout
        """
        elapsed = 0
        
        while elapsed < max_wait_seconds:
            result = await self.get_prediction(prediction_id)
            
            if not result:
                return None
            
            status = result.get("status")
            
            if status == "succeeded":
                output = result.get("output")
                if output and isinstance(output, list) and len(output) > 0:
                    image_url = output[0]
                    logger.info(f"🖼️ ✅ Image ready: {image_url[:50]}...")
                    return image_url
                else:
                    logger.warning(f"🖼️ ⚠️ No output in result")
                    return None
                    
            elif status == "failed":
                error = result.get("error")
                logger.error(f"🖼️ ❌ Prediction failed: {error}")
                return None
                
            elif status == "canceled":
                logger.warning(f"🖼️ ⚠️ Prediction canceled")
                return None
            
            # עדיין בתהליך
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.warning(f"🖼️ ⚠️ Timeout waiting for prediction {prediction_id}")
        return None
    
    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        wait_for_result: bool = True,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        פונקציה מאוחדת ליצירת תמונה
        
        Args:
            prompt: תיאור התמונה
            aspect_ratio: יחס גובה-רוחב
            wait_for_result: האם להמתין לתוצאה
            **kwargs: פרמטרים נוספים ל-create_prediction
            
        Returns:
            dict עם image_url ופרטים נוספים
        """
        # יצירת prediction
        prediction = await self.create_prediction(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            **kwargs
        )
        
        if not prediction:
            return None
        
        prediction_id = prediction.get("prediction_id")
        
        if not wait_for_result:
            return {
                "prediction_id": prediction_id,
                "status": "processing",
                "image_url": None
            }
        
        # המתנה לתוצאה
        image_url = await self.wait_for_result(prediction_id)
        
        if image_url:
            return {
                "prediction_id": prediction_id,
                "status": "succeeded",
                "image_url": image_url
            }
        else:
            return {
                "prediction_id": prediction_id,
                "status": "failed",
                "image_url": None
            }
    
    async def generate_post_image(
        self,
        image_prompt: str,
        style: str = "professional marketing"
    ) -> Optional[str]:
        """
        יצירת תמונה לפוסט פייסבוק
        
        Args:
            image_prompt: תיאור התמונה (מ-GPT/Claude)
            style: סגנון התמונה
            
        Returns:
            URL של התמונה, או None
        """
        # הוספת הדוגמן eyal וסגנון ל-prompt (פוסט אישי)
        enhanced_prompt = f"A photo of eyal, {image_prompt}, {style}, high quality, 4k, professional photography"
        
        result = await self.generate_image(
            prompt=enhanced_prompt,
            aspect_ratio="16:9",  # מתאים לפייסבוק
            wait_for_result=True,
            num_outputs=1,
            hf_lora="eyalafteru/eyalnew"  # Custom LoRA model
        )
        
        if result and result.get("status") == "succeeded":
            return result.get("image_url")
        
        return None


# Singleton
_replicate_service: Optional[ReplicateImageService] = None


def get_replicate_service() -> ReplicateImageService:
    """קבלת instance של Replicate Service"""
    global _replicate_service
    if _replicate_service is None:
        _replicate_service = ReplicateImageService()
    return _replicate_service
