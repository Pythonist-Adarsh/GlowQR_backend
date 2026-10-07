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

from fastapi.responses import JSONResponse
import time

@router.post("/{business_id}/check")
async def trigger_visibility_check(business_id: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        return JSONResponse(status_code=404, content={"message": "Business not found"})
        
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not gemini_api_key and not openai_api_key:
        return JSONResponse(status_code=500, content={"message": "No AI API keys configured", "error_type": "Engine not configured"})
        
    # Rate limit check
    cooldown_hours = 6
    if business.slug == "house-of-aadayein-a4d823":
        cooldown_hours = 30 / 3600 # 30 seconds
        
    cooldown_delta = timedelta(hours=cooldown_hours)
    cutoff_time = datetime.now(timezone.utc) - cooldown_delta
    
    recent_log = db.query(models_ai.AIVisibilityLog).filter(
        models_ai.AIVisibilityLog.business_id == business.id,
        models_ai.AIVisibilityLog.created_at >= cutoff_time
    ).order_by(models_ai.AIVisibilityLog.created_at.desc()).first()
    
    if recent_log:
        time_passed = datetime.now(timezone.utc) - recent_log.created_at.replace(tzinfo=timezone.utc)
        retry_after = (cooldown_delta - time_passed).total_seconds()
        
        hours = int(retry_after // 3600)
        minutes = int((retry_after % 3600) // 60)
        seconds = int(retry_after % 60)
        
        msg = f"Rate limited, try again in {hours}h {minutes}m" if hours > 0 else (f"Rate limited, try again in {minutes}m {seconds}s" if minutes > 0 else f"Rate limited, try again in {seconds}s")
        
        return JSONResponse(status_code=429, content={
            "message": msg,
            "retry_after": retry_after
        })
        
    current_run_id = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    location = format_location(business.area_locality, business.city)
    branded_query = f"best {business.category} in {location}"
    
    # Get queries
    queries = []
    if getattr(business, "visibility_queries", None):
        queries = list(business.visibility_queries)
        
    if branded_query not in queries:
        queries.insert(0, branded_query)
        
    queries = queries[:8]
    
    active_engines = []
    if gemini_api_key: active_engines.append("gemini")
    if openai_api_key: active_engines.append("chatgpt")
    
    start_time = time.time()
    print(f"[AI Visibility] Starting check for slug: {business.slug}, engines: {active_engines}, queries: {len(queries)}")
    
    engine_responses = []
    
    for engine in active_engines:
        engine_start = time.time()
        tasks = []
        for q in queries:
            tasks.append(check_engine(engine, q))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        engine_ok = True
        error_type = None
        saved_count = 0
        
        for q, res in zip(queries, results):
            if isinstance(res, Exception):
                print(f"[AI Visibility] Engine {engine} exception for '{q}': {res}")
                engine_ok = False
                error_type = str(res)
                continue
                
            if "error" in res:
                print(f"[AI Visibility] Engine {engine} error for '{q}': {res['error']}")
                engine_ok = False
                error_type = res["error"]
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
            saved_count += 1
            
        engine_duration = time.time() - engine_start
        print(f"[AI Visibility] Engine {engine} completed in {engine_duration:.2f}s. Outcome: {'OK' if engine_ok else 'ERROR'}, Saved: {saved_count}")
        
        engine_responses.append({
            "engine": engine,
            "status": "ok" if engine_ok else "error",
            "error_type": error_type,
            "results_saved": saved_count
        })
        
    db.commit()
    
    total_duration = time.time() - start_time
    print(f"[AI Visibility] Check fully completed in {total_duration:.2f}s for {business.slug}")
    
    return {"success": True, "engines": engine_responses}
