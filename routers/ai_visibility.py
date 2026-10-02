import os
import httpx
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import models_ai
import re
import json
from utils_ai import format_location, extract_competitors

router = APIRouter(prefix="/api/ai-visibility", tags=["AI Visibility"])

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
        "snippet": log.response_snippet,
        "query": log.query,
        "raw_response": log.raw_response
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
    
    location = format_location(business.area_locality, business.city)
    prompt = f"best {business.category} in {location}"
    
    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}",
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
                comp_list = await extract_competitors(text)
                if comp_list:
                    competitor_mentioned = ", ".join(comp_list)
                else:
                    competitor_mentioned = "No specific brands named"
                    
            log = models_ai.AIVisibilityLog(
                business_id=business.id,
                month=current_month,
                engine="gemini",
                mentioned=mentioned,
                response_snippet=text[:1000] if text else "Empty response",
                raw_response=text,
                competitor_mentioned=competitor_mentioned,
                query=prompt
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
                "snippet": log.response_snippet,
                "query": log.query,
                "raw_response": log.raw_response
            }
        else:
            raise HTTPException(status_code=500, detail=f"Gemini API returned {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
