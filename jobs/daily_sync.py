import sys
import os
import time
from datetime import datetime, timezone

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
import models
from services.places_service import fetch_place_details

def sync_all_businesses():
    print("Starting daily Google Maps sync...")
    db = SessionLocal()
    try:
        # Fetch ALL active businesses from DB
        businesses = db.query(models.Business).filter(
            models.Business.place_id.isnot(None),
            models.Business.place_id != ''
        ).all()

        print(f"Found {len(businesses)} businesses to sync.")
        synced, failed = 0, 0
        now_utc = datetime.now(timezone.utc)

        for biz in businesses:
            try:
                data = fetch_place_details(biz.place_id)
                if not data:
                    print(f"[WARNING] {biz.name}: Places API returned nothing")
                    failed += 1
                    continue

                current_rating = data.get("rating", 0)
                current_count = data.get("userRatingCount", 0)

                # Update businesses table
                biz.google_rating = current_rating
                biz.review_count = current_count
                biz.last_synced_at = now_utc
                # NEVER touch business.baseline_review_count
                
                db.commit()

                print(f"[SUCCESS] {biz.name}: {current_rating} stars | {current_count} reviews")
                synced += 1

            except Exception as e:
                db.rollback()
                print(f"[ERROR] {biz.name}: {e}")
                failed += 1

            # Removed artificial SerpAPI rate limit, Places API handles concurrency better but keep a tiny pause
            time.sleep(0.1)

        timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"\nSynced {synced} businesses at {timestamp_str}. Failed: {failed}")
        return {"synced": synced, "failed": failed, "timestamp": timestamp_str, "status": "success"}

    finally:
        db.close()

if __name__ == "__main__":
    sync_all_businesses()
