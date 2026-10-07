import os
import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import models_ai
import json
from utils_ai import format_location
from services.visibility_engine import check_engine

router = APIRouter(prefix="/api/ai-visibility", tags=["AI Visibility"])

@router.get("/{business_id}")
async def get_latest_visibility(business_id: str, db: Session = Depends(get_db)):
    # Find the most recent run (by month/timestamp identifier)
    latest_log = db.query(models_ai.AIVisibilityLog).filter(
        models_ai.AIVisibilityLog.business_id == business_id
    ).order_by(models_ai.AIVisibilityLog.created_at.desc()).first()
    
    if not latest_log:
        return {"has_data": False}
        
    latest_run_id = latest_log.month
    
    logs = db.query(models_ai.AIVisibilityLog).filter(
        models_ai.AIVisibilityLog.business_id == business_id,
        models_ai.AIVisibilityLog.month == latest_run_id
    ).all()
    
    engines = {}
    competitors_set = set()
    
    for log in logs:
        if log.engine not in engines:
            engines[log.engine] = {
                "engine": log.engine,
                "last_checked": log.created_at.isoformat(),
                "queries": [],
                "mentioned_count": 0,
                "total_count": 0
            }
            
        engines[log.engine]["queries"].append({
            "query": log.query,
            "mentioned": log.mentioned,
            "sources": log.sources,
            "sourced_from_us": log.sourced_from_us,
            "snippet": log.response_snippet
        })
        
        engines[log.engine]["total_count"] += 1
        if log.mentioned:
            engines[log.engine]["mentioned_count"] += 1
            
        if log.competitor_mentioned and log.competitor_mentioned != "N/A" and log.competitor_mentioned != "No specific brands named":
            for comp in log.competitor_mentioned.split(", "):
                if comp.strip():
                    competitors_set.add(comp.strip())
                    
    has_chatgpt_key = bool(os.getenv("OPENAI_API_KEY"))
                    
    return {
        "has_data": True,
        "engines": list(engines.values()),
        "competitors": list(competitors_set) if competitors_set else ["No specific brands named"],
        "has_chatgpt_key": has_chatgpt_key
    }

@router.post("/{business_id}/check")
async def trigger_visibility_check(business_id: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not gemini_api_key and not openai_api_key:
        raise HTTPException(status_code=500, detail="No AI API keys configured")
        
    # Rate limit check: once per 6 hours
    six_hours_ago = datetime.now(timezone.utc) - timedelta(hours=6)
    recent_log = db.query(models_ai.AIVisibilityLog).filter(
        models_ai.AIVisibilityLog.business_id == business.id,
        models_ai.AIVisibilityLog.created_at >= six_hours_ago
    ).first()
    
    if recent_log:
        raise HTTPException(status_code=429, detail="Visibility check was run recently. Please wait 6 hours.")
        
    current_run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    location = format_location(business.area_locality, business.city)
    branded_query = f"best {business.category} in {location}"
    
    # Get queries
    queries = []
    if getattr(business, "visibility_queries", None):
        queries = list(business.visibility_queries)
        
    if branded_query not in queries:
        queries.insert(0, branded_query)
        
    # Cap to 8 queries
    queries = queries[:8]
    
    # Determine engines to run
    active_engines = []
    if gemini_api_key:
        active_engines.append("gemini")
    if openai_api_key:
        active_engines.append("chatgpt")
        
    # Build tasks
    tasks = []
    task_metadata = []
    
    for engine in active_engines:
        for q in queries:
            tasks.append(check_engine(engine, q))
            task_metadata.append({"engine": engine, "query": q})
            
    # Run in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    saved_logs = []
    for meta, res in zip(task_metadata, results):
        engine = meta["engine"]
        q = meta["query"]
        
        if isinstance(res, Exception):
            print(f"Engine {engine} query '{q}' raised exception: {res}")
            continue
            
        if "error" in res:
            print(f"Engine {engine} query '{q}' returned error: {res['error']}")
            continue
            
        snippet = res.get("raw_text", "")
        if len(snippet) > 1000:
            snippet = snippet[:1000] + "..."
            
        log = models_ai.AIVisibilityLog(
            business_id=business.id,
            month=current_run_id,
            engine=engine,
            query=q,
            mentioned=res.get("mentioned", False),
            sourced_from_us=res.get("sourced_from_us", False),
            sources=res.get("sources", []),
            raw_response=res.get("raw_text", ""),
            response_snippet=snippet,
            competitor_mentioned=res.get("competitors_raw", "N/A")
        )
        db.add(log)
        saved_logs.append(log)
        
    db.commit()
    
    return {"success": True, "logs_saved": len(saved_logs)}
