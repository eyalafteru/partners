"""
PartnerCalc OS - Scenarios API Routes
ניהול תרחישי תשובות אוטומטיות
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from ...database import get_db
from ...models.reply_scenario import ReplyScenario
from ...data.default_scenarios import get_default_scenarios

router = APIRouter(tags=["Admin - Scenarios"])


# ========== Pydantic Models ==========
class ScenarioCreate(BaseModel):
    name: str
    display_name: str
    category: str = "positive"
    keywords: List[str] = []
    response_subject: Optional[str] = None
    response_body: str
    requires_human: bool = False
    priority: int = 50
    is_active: bool = True
    sender_name: str = "אייל עובדיה"
    sender_title: str = "מנהל מקצועי | רק תבקש"


class ScenarioUpdate(BaseModel):
    display_name: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    response_subject: Optional[str] = None
    response_body: Optional[str] = None
    requires_human: Optional[bool] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    sender_name: Optional[str] = None
    sender_title: Optional[str] = None


# ========== API Routes ==========
@router.get("")
async def list_scenarios(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """רשימת כל התרחישים"""
    query = db.query(ReplyScenario)
    
    if category:
        query = query.filter(ReplyScenario.category == category)
    
    if is_active is not None:
        query = query.filter(ReplyScenario.is_active == is_active)
    
    scenarios = query.order_by(ReplyScenario.priority.desc()).all()
    
    return {
        "scenarios": [s.to_dict() for s in scenarios],
        "total": len(scenarios)
    }


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """קבלת תרחיש לפי ID"""
    scenario = db.query(ReplyScenario).filter(ReplyScenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    return scenario.to_dict()


@router.post("")
async def create_scenario(data: ScenarioCreate, db: Session = Depends(get_db)):
    """יצירת תרחיש חדש"""
    # בדיקה שהשם לא קיים
    existing = db.query(ReplyScenario).filter(ReplyScenario.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Scenario with this name already exists")
    
    scenario = ReplyScenario(
        name=data.name,
        display_name=data.display_name,
        category=data.category,
        keywords=data.keywords,
        response_subject=data.response_subject,
        response_body=data.response_body,
        requires_human=data.requires_human,
        priority=data.priority,
        is_active=data.is_active,
        sender_name=data.sender_name,
        sender_title=data.sender_title,
    )
    
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    
    return scenario.to_dict()


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: int,
    data: ScenarioUpdate,
    db: Session = Depends(get_db)
):
    """עדכון תרחיש"""
    scenario = db.query(ReplyScenario).filter(ReplyScenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(scenario, key, value)
    
    db.commit()
    db.refresh(scenario)
    
    return scenario.to_dict()


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """מחיקת תרחיש"""
    scenario = db.query(ReplyScenario).filter(ReplyScenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    db.delete(scenario)
    db.commit()
    
    return {"status": "deleted", "id": scenario_id}


@router.post("/seed")
async def seed_scenarios(force_update: bool = False, db: Session = Depends(get_db)):
    """טעינת תרחישי ברירת מחדל (14 תרחישים)
    force_update=true יעדכן גם תרחישים קיימים
    """
    default_scenarios = get_default_scenarios()
    
    created = 0
    updated = 0
    skipped = 0
    
    for scenario_data in default_scenarios:
        # בדיקה אם כבר קיים
        existing = db.query(ReplyScenario).filter(
            ReplyScenario.name == scenario_data["name"]
        ).first()
        
        if existing:
            if force_update:
                # עדכון הערכים
                existing.display_name = scenario_data["display_name"]
                existing.category = scenario_data["category"]
                existing.keywords = scenario_data["keywords"]
                existing.response_subject = scenario_data["response_subject"]
                existing.response_body = scenario_data["response_body"]
                existing.requires_human = scenario_data["requires_human"]
                existing.priority = scenario_data["priority"]
                existing.sender_name = scenario_data.get("sender_name", "אייל עובדיה")
                existing.sender_title = scenario_data.get("sender_title", "מנהל מקצועי | רק תבקש")
                updated += 1
                continue
            else:
                skipped += 1
                continue
        
        scenario = ReplyScenario(
            name=scenario_data["name"],
            display_name=scenario_data["display_name"],
            category=scenario_data["category"],
            keywords=scenario_data["keywords"],
            response_subject=scenario_data["response_subject"],
            response_body=scenario_data["response_body"],
            requires_human=scenario_data["requires_human"],
            priority=scenario_data["priority"],
            is_active=scenario_data["is_active"],
            sender_name=scenario_data.get("sender_name", "אייל עובדיה"),
            sender_title=scenario_data.get("sender_title", "מנהל מקצועי | רק תבקש"),
        )
        
        db.add(scenario)
        created += 1
    
    db.commit()
    
    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "total": len(default_scenarios)
    }


@router.post("/{scenario_id}/toggle")
async def toggle_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """הפעלה/כיבוי תרחיש"""
    scenario = db.query(ReplyScenario).filter(ReplyScenario.id == scenario_id).first()
    
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    scenario.is_active = not scenario.is_active
    db.commit()
    
    return {
        "id": scenario_id,
        "is_active": scenario.is_active
    }


@router.get("/categories/list")
async def get_categories():
    """רשימת קטגוריות זמינות"""
    return {
        "categories": [
            {"value": "positive", "label": "חיובי", "color": "green"},
            {"value": "negative", "label": "שלילי", "color": "red"},
            {"value": "question", "label": "שאלה", "color": "blue"},
            {"value": "technical", "label": "טכני", "color": "purple"},
            {"value": "deferral", "label": "דחייה", "color": "yellow"},
            {"value": "human", "label": "העברה לאנושי", "color": "orange"},
        ]
    }
