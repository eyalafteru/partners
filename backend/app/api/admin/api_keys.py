"""API Keys Management Routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from ...database import get_db
from ...models.api_key import ApiKey
from cryptography.fernet import Fernet
import os
import json

router = APIRouter(tags=["Admin - API Keys"])

# Get encryption key from environment or generate one
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def mask_value(value: str, show_chars: int = 4) -> str:
    """Mask a sensitive value, showing only last few characters."""
    if len(value) <= show_chars:
        return "****"
    return "*" * (len(value) - show_chars) + value[-show_chars:]


@router.get("")
async def list_api_keys(db: Session = Depends(get_db)):
    """List all configured API keys (masked)."""
    keys = db.query(ApiKey).all()
    result = []
    
    for key in keys:
        # Decrypt and mask credentials
        try:
            if key.encrypted_credentials:
                decrypted = cipher.decrypt(key.encrypted_credentials.encode()).decode()
                creds = json.loads(decrypted)
                masked = {k: mask_value(str(v)) for k, v in creds.items()}
            else:
                masked = {}
        except Exception:
            masked = {"error": "Unable to decrypt"}
        
        result.append({
            "id": key.id,
            "service_name": key.service_name,
            "display_name": key.display_name,
            "is_active": key.is_active,
            "last_verified": key.last_verified.isoformat() if key.last_verified else None,
            "last_error": key.last_error,
            "usage_stats": key.usage_stats or {},
            "credentials_masked": masked
        })
    
    return result


@router.post("")
async def create_api_key(data: dict, db: Session = Depends(get_db)):
    """Create a new API key configuration."""
    # Check if service already exists
    existing = db.query(ApiKey).filter(ApiKey.service_name == data["service_name"]).first()
    if existing:
        raise HTTPException(status_code=400, detail="Service already configured")
    
    # Encrypt credentials
    credentials_json = json.dumps(data.get("credentials", {}))
    encrypted = cipher.encrypt(credentials_json.encode()).decode()
    
    api_key = ApiKey(
        service_name=data["service_name"],
        display_name=data.get("display_name", data["service_name"]),
        encrypted_credentials=encrypted,
        is_active=True
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return {"id": api_key.id, "service_name": api_key.service_name}


@router.put("/{service_name}")
async def update_api_key(
    service_name: str,
    data: dict,
    db: Session = Depends(get_db)
):
    """Update an existing API key."""
    api_key = db.query(ApiKey).filter(ApiKey.service_name == service_name).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="Service not found")
    
    if "display_name" in data:
        api_key.display_name = data["display_name"]
    
    if "credentials" in data:
        credentials_json = json.dumps(data["credentials"])
        api_key.encrypted_credentials = cipher.encrypt(credentials_json.encode()).decode()
    
    if "is_active" in data:
        api_key.is_active = data["is_active"]
    
    db.commit()
    return {"status": "updated"}


@router.delete("/{service_name}")
async def delete_api_key(service_name: str, db: Session = Depends(get_db)):
    """Delete an API key configuration."""
    api_key = db.query(ApiKey).filter(ApiKey.service_name == service_name).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="Service not found")
    
    db.delete(api_key)
    db.commit()
    return {"status": "deleted"}


@router.post("/{service_name}/verify")
async def verify_api_key(service_name: str, db: Session = Depends(get_db)):
    """Verify an API key connection."""
    api_key = db.query(ApiKey).filter(ApiKey.service_name == service_name).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="Service not found")
    
    # Decrypt credentials
    try:
        decrypted = cipher.decrypt(api_key.encrypted_credentials.encode()).decode()
        credentials = json.loads(decrypted)
    except Exception as e:
        api_key.last_error = f"Decryption failed: {str(e)}"
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to decrypt credentials")
    
    # Verify based on service type
    verified = False
    error_msg = None
    
    try:
        if service_name == "whatsapp":
            # Verify Green-API connection
            import httpx
            instance_id = credentials.get("instance_id")
            token = credentials.get("api_key") or credentials.get("token")
            if instance_id and token:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://api.green-api.com/waInstance{instance_id}/getStateInstance/{token}",
                        timeout=10
                    )
                    verified = resp.status_code == 200
        
        elif service_name == "ollama":
            # Verify Ollama connection
            import httpx
            host = credentials.get("host", "localhost")
            port = credentials.get("port", 11434)
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"http://{host}:{port}/api/version", timeout=5)
                verified = resp.status_code == 200
        
        else:
            # For other services, just check if credentials exist
            verified = bool(credentials)
            
    except Exception as e:
        error_msg = str(e)
    
    # Update API key status
    api_key.last_verified = datetime.utcnow()
    api_key.is_active = verified
    if error_msg:
        api_key.last_error = error_msg
    else:
        api_key.last_error = None
    
    db.commit()
    
    return {
        "service_name": service_name,
        "verified": verified,
        "error": error_msg
    }
