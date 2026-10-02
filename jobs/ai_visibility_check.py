import os
import httpx
from datetime import datetime, timezone
from database import SessionLocal
import models
import models_ai
import json
from utils_ai import format_location, extract_competitors_sync

def run_monthly_ai_visibility_check():
    db = SessionLocal()
    try:
        # Check if House of Aadayein exists
        business = db.query(models.Business).filter(models.Business.name.ilike("%House of Aadayein%")).first()
        if not business:
            print("House of Aadayein business not found for visibility check")
            return
            
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            print("No GEMINI_API_KEY found, skipping visibility check")
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
        
        prompts = [
            f"best {business.category} in {location}",
            f"top rated {business.category} near {business.area_locality}",
            f"where to go for {business.category} in {business.city}"
        ]
        
        results = []
        for prompt in prompts:
            try:
                response = httpx.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    
                    mentioned = "house of aadayein" in text.lower() or "house of adayein" in text.lower()
                    competitor_mentioned = "N/A"
                    if not mentioned and text:
                        comp_list = extract_competitors_sync(text)
                        if comp_list:
                            competitor_mentioned = ", ".join(comp_list)
                        else:
                            competitor_mentioned = "No specific brands named"

                    # Log it
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
                    results.append(log)
            except Exception as e:
                print(f"Error calling Gemini API for prompt '{prompt}': {e}")
                
        if results:
            db.commit()
            print(f"Successfully logged {len(results)} visibility checks for House of Aadayein")
            
    except Exception as e:
        print(f"Error in monthly AI visibility check: {e}")
    finally:
        db.close()
