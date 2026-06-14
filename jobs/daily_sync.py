import sys
import os
import time
from datetime import datetime, timezone

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from services.serpapi_service import fetch_place_details

def run_daily_sync():
    print("Starting daily Google Maps sync...")
    db = SessionLocal()
    try:
        businesses = db.query(models.Business).join(models.User).filter(
            models.Business.place_id.isnot(None),
            models.Business.place_id != '',
            models.Business.is_onboarded == True,
            models.User.plan.in_(['trial', 'basic', 'premium'])
        ).all()

        print(f"Found {len(businesses)} businesses to sync.")
        synced, failed = 0, 0

        for biz in businesses:
            try:
                data = fetch_place_details(biz.place_id)
                if not data:
                    print(f"[WARNING] {biz.name}: SerpAPI returned nothing")
                    failed += 1
                    continue

                current_rating = data["google_rating"]
                current_count = data["review_count"]
                
                baseline_count = biz.review_count or 0
                new_reviews = max(0, current_count - baseline_count)

                # Save snapshot to history using SQLAlchemy ORM
                # We check if there's already a snapshot today
                now_utc = datetime.now(timezone.utc)
                # Approximation: we can use UTC date for uniqueness in ORM
                today = now_utc.date()
                
                # Check if entry exists for today
                existing_history = db.query(models.GoogleRatingHistory).filter(
                    models.GoogleRatingHistory.business_id == biz.id
                ).all()
                
                # Manual filter for same day
                today_history = [h for h in existing_history if h.fetched_at and h.fetched_at.date() == today]

                if today_history:
                    history = today_history[0]
                    history.rating = current_rating
                    history.review_count = current_count
                else:
                    history = models.GoogleRatingHistory(
                        business_id=biz.id,
                        rating=current_rating,
                        review_count=current_count,
                        fetched_at=now_utc
                    )
                    db.add(history)

                # Update businesses table
                biz.google_rating = current_rating
                biz.review_count = current_count
                biz.last_google_sync = now_utc

                db.commit()

                print(f"[SUCCESS] {biz.name}: {current_rating} stars | {current_count} reviews (+{new_reviews} since baseline)")
                synced += 1

            except Exception as e:
                db.rollback()
                print(f"[ERROR] {biz.name}: {e}")
                failed += 1

            time.sleep(1)  # 1 req/sec SerpAPI rate limit

        print(f"\nDone: {synced} synced, {failed} failed")
        return {"synced": synced, "failed": failed}

    finally:
        db.close()

if __name__ == "__main__":
    run_daily_sync()
