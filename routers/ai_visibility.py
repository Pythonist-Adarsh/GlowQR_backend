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

async def extract_competitors(text: str) -> list[str]:
    system_prompt = "From the text below, extract ONLY names of real businesses/brands recommended as places to buy from. Exclude headings, categories, locations, product types, and generic phrases. Return strictly a JSON array of strings, max 8, no other text."
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")
    
    llm_text = ""
    try:
        if groq_key:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
        
    if not llm_text and deepinfra_key:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    headers={"Authorization": f"Bearer {deepinfra_key}"},
                    json={
                        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    if not llm_text:
        return []

    llm_text = llm_text.strip()
    if llm_text.startswith("```json"):
        llm_text = llm_text[7:]
    elif llm_text.startswith("```"):
        llm_text = llm_text[3:]
    if llm_text.endswith("```"):
        llm_text = llm_text[:-3]
    
    try:
        parsed = json.loads(llm_text.strip())
        if not isinstance(parsed, list):
            return []
            
        final_list = []
        seen = set()
        for item in parsed:
            if not isinstance(item, str): continue
            clean = item.strip().rstrip(":")
            if not clean: continue
            if len(clean) > 40: continue
            if ":" in clean or "(" in clean: continue
            
            lower_clean = clean.lower()
            if "house of aadayein" in lower_clean or "aadayein" in lower_clean or "adayein" in lower_clean:
                continue
                
            if lower_clean not in seen:
                seen.add(lower_clean)
                final_list.append(clean)
                
        return final_list
    except json.JSONDecodeError:
        return []

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
    
    loc_parts = []
    if business.area_locality:
        loc_parts.append(business.area_locality.strip())
    if business.city:
        city = business.city.strip()
        if not any(city.lower() in part.lower() for part in loc_parts):
            loc_parts.append(city)
    location = ", ".join(loc_parts) if loc_parts else "your area"
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
                    competitor_mentioned = "Other local businesses"
                    
            log = models_ai.AIVisibilityLog(
                business_id=business.id,
                month=current_month,
                engine="gemini",
                mentioned=mentioned,
                response_snippet=text[:1000] if text else "Empty response",
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
                "snippet": log.response_snippet
            }
        else:
            raise HTTPException(status_code=500, detail=f"Gemini API returned {response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
