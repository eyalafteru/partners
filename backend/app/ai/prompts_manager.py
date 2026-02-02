"""
PartnerCalc OS - Prompts Manager
ניהול פרומפטים דינמי
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.prompt import Prompt, AILog


class PromptsManager:
    """
    מנהל פרומפטים - טעינה, עדכון, וניהול של פרומפטים
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: Dict[str, Prompt] = {}
    
    async def get_prompt(self, node_name: str) -> Optional[Prompt]:
        """
        קבלת פרומפט לפי שם הצומת
        """
        # בדיקה בקאש
        if node_name in self._cache:
            return self._cache[node_name]
        
        # שליפה מ-DB
        result = await self.session.execute(
            select(Prompt).where(Prompt.node_name == node_name)
        )
        prompt = result.scalar_one_or_none()
        
        if prompt:
            self._cache[node_name] = prompt
        
        return prompt
    
    async def get_all_prompts(self, active_only: bool = True) -> List[Prompt]:
        """
        קבלת כל הפרומפטים
        """
        query = select(Prompt)
        if active_only:
            query = query.where(Prompt.is_active == True)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def update_prompt(
        self,
        node_name: str,
        updates: Dict[str, Any]
    ) -> Prompt:
        """
        עדכון פרומפט
        """
        prompt = await self.get_prompt(node_name)
        if not prompt:
            raise ValueError(f"Prompt '{node_name}' not found")
        
        for field, value in updates.items():
            if hasattr(prompt, field):
                setattr(prompt, field, value)
        
        # עדכון קאש
        self._cache[node_name] = prompt
        
        await self.session.flush()
        return prompt
    
    async def render_prompt(
        self,
        node_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        הרנדור פרומפט עם החלפת משתנים
        """
        prompt = await self.get_prompt(node_name)
        if not prompt:
            raise ValueError(f"Prompt '{node_name}' not found")
        
        rendered = prompt.user_prompt_template
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            rendered = rendered.replace(placeholder, str(value))
        
        return rendered
    
    async def get_prompt_stats(self, node_name: str) -> Dict[str, Any]:
        """
        קבלת סטטיסטיקות לפרומפט
        """
        from sqlalchemy import func
        
        prompt = await self.get_prompt(node_name)
        if not prompt:
            raise ValueError(f"Prompt '{node_name}' not found")
        
        # סה"כ קריאות
        result = await self.session.execute(
            select(func.count(AILog.id))
            .where(AILog.prompt_id == prompt.id)
        )
        total_calls = result.scalar()
        
        # קריאות מוצלחות
        result = await self.session.execute(
            select(func.count(AILog.id))
            .where(AILog.prompt_id == prompt.id, AILog.success == True)
        )
        success_calls = result.scalar()
        
        # זמן ריצה ממוצע
        result = await self.session.execute(
            select(func.avg(AILog.execution_time_ms))
            .where(AILog.prompt_id == prompt.id)
        )
        avg_time = result.scalar()
        
        return {
            "node_name": node_name,
            "total_calls": total_calls,
            "success_calls": success_calls,
            "success_rate": (success_calls / total_calls * 100) if total_calls > 0 else 0,
            "avg_execution_time_ms": round(avg_time) if avg_time else 0
        }
    
    def clear_cache(self):
        """
        ניקוי הקאש
        """
        self._cache.clear()


async def get_prompts_manager(session: AsyncSession) -> PromptsManager:
    """
    Factory function לקבלת PromptsManager
    """
    return PromptsManager(session)
