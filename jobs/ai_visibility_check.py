import os
import httpx
from datetime import datetime, timezone
from database import SessionLocal
import models
import models_ai
import json
import asyncio
from utils_ai import format_location
from services.visibility_engine import check_engine

def run_monthly_ai_visibility_check():
    db = SessionLocal()
    try:
        # Check if House of Aadayein exists
        business = db.query(models.Business).filter(models.Business.name.ilike("%House of Aadayein%")).first()
        if not business:
            print("House of Aadayein business not found for visibility check")
            return
            
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if not gemini_api_key and not openai_api_key:
            print("No API keys found, skipping visibility check")
            return
            
        current_month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        # Check if we already ran for this month
        existing_log = db.query(models_ai.AIVisibilityLog).filter(
            models_ai.AIVisibilityLog.business_id == business.id,
            models_ai.AIVisibilityLog.month == current_month
        ).first()
        
        if existing_log:
            print(f"Visibility check already ran for {current_month}")
            return
            
        location = format_location(business.area_locality, business.city)
        branded_query = f"best {business.category} in {location}"
        
        prompts = []
        if getattr(business, "visibility_queries", None):
            prompts = list(business.visibility_queries)
            
        if branded_query not in prompts:
            prompts.insert(0, branded_query)
            
        prompts = prompts[:8]
        
        engines = []
        if gemini_api_key: engines.append("gemini")
        if openai_api_key: engines.append("chatgpt")
        
        async def run_checks():
            tasks = []
            meta = []
            for e in engines:
                for p in prompts:
                    tasks.append(check_engine(e, p))
                    meta.append((e, p))
                    
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return meta, results
            
        meta, results = asyncio.run(run_checks())
        
        saved = 0
        for (e, p), res in zip(meta, results):
            if isinstance(res, Exception):
                print(f"Exception for {e} '{p}': {res}")
                continue
            if "error" in res:
                print(f"Error for {e} '{p}': {res['error']}")
                continue
                
            snippet = res.get("raw_text", "")
            if len(snippet) > 1000:
                snippet = snippet[:1000] + "..."
                
            log = models_ai.AIVisibilityLog(
                business_id=business.id,
                month=current_month,
                engine=e,
                mentioned=res.get("mentioned", False),
                response_snippet=snippet,
                raw_response=res.get("raw_text", ""),
                competitor_mentioned=res.get("competitors_raw", "N/A"),
                query=p,
                sourced_from_us=res.get("sourced_from_us", False),
                sources=res.get("sources", [])
            )
            db.add(log)
            saved += 1
            
        if saved > 0:
            db.commit()
            print(f"Successfully logged {saved} visibility checks for House of Aadayein")
            
    except Exception as e:
        print(f"Error in monthly AI visibility check: {e}")
    finally:
        db.close()
