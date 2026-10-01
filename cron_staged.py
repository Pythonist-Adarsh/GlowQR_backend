import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def run_weekly_ai_profile_extraction():
    db = SessionLocal()
    try:
        # Check if House of Aadayein has new reviews since last_generated_at
        business = db.query(models.Business).filter(models.Business.name.ilike("%House of Aadayein%")).first()
        if not business:
            return
            
        import models_ai
        profile = db.query(models_ai.BusinessAIProfile).filter(models_ai.BusinessAIProfile.business_id == business.id).first()
        
        last_generated = profile.last_generated_at if profile else None
        
        query = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == business.id,
            models.ScanEvent.review_text.isnot(None),
            models.ScanEvent.review_text != ''
        )
        if last_generated:
            query = query.filter(models.ScanEvent.scanned_at > last_generated)
            
        new_reviews = query.all()
        
        if new_reviews or not profile:
            # We have new reviews (or no profile yet). Let's call the extraction logic directly.
            # We can reuse the router's function or call it via HTTP. Let's just import and call it.
            # Actually, to avoid async issues in sync cron, we can use requests to call localhost or run the logic here.
            import httpx
            import os
            try:
                # Call local endpoint
                port = os.getenv("PORT", "10000")
                httpx.post(f"http://127.0.0.1:{port}/ai-profile/extract", timeout=60.0)
                print("Successfully triggered weekly AI profile extraction for House of Aadayein")
            except Exception as e:
                print(f"Error calling ai-profile extraction: {e}")
                
    except Exception as e:
        print(f"Error in weekly AI profile extraction: {e}")
    finally:
        db.close()
