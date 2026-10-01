import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import models_ai
import re

router = APIRouter(prefix="/ai-visibility", tags=["AI Visibility"])

@router.get("/{business_id}")
async def get_latest_visibility(business_id: str, db: Session = Depends(get_db)):
    log = db.query(models_ai.AIVisibilityLog).filter(
        models_ai.AIVisibilityLog.business_id == business_id,
        models_ai.AIVisibilityLog.engine == "gemini"
    ).order_by(models_ai.AIVisibilityLog.created_at.desc()).first()
    
    if not log:
        return {"has_data": False}
        
    return {
        "has_data": True,
        "mentioned": log.mentioned,
        "last_checked": log.created_at.isoformat(),
        "competitor_mentioned": log.competitor_mentioned,
        "engine": log.engine,
        "snippet": log.response_snippet
    }

@router.post("/{business_id}/check")
async def trigger_visibility_check(business_id: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
    current_month = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S") # Just use timestamp so we can trigger multiple times manually
    prompt = f"best {business.category} in {business.area_locality}, {business.city}"
    
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            b_name = business.name.lower()
            mentioned = b_name in text.lower() or "house of adayein" in text.lower() or "house of aadayein" in text.lower()
            
            competitor_mentioned = "N/A"
            if not mentioned and text:
                # Try to extract the first bolded item or first numbered item
                matches = re.findall(r'(?:\d+\.\s)?\*\*(.*?)\*\*', text)
                if matches:
                    competitor_mentioned = ", ".join(matches[:3])
                else:
                    competitor_mentioned = "Other local businesses"
                    
            log = models_ai.AIVisibilityLog(
                business_id=business.id,
                month=current_month,
                engine="gemini",
                mentioned=mentioned,
                response_snippet=text[:1000] if text else "Empty response",
                competitor_mentioned=competitor_mentioned
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            
            return {
                "success": True,
                "mentioned": log.mentioned,
                "last_checked": log.created_at.isoformat(),
                "competitor_mentioned": log.competitor_mentioned,
                "engine": log.engine,
                "snippet": log.response_snippet
            }
        else:
            raise HTTPException(status_code=500, detail=f"Gemini API returned {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
