import dependencies
from database import SessionLocal
import models
from datetime import datetime

def fix_missing_negative_feedbacks():
    db = SessionLocal()
    try:
        # Find all scan events with 1 or 2 stars that don't have a negative feedback
        scans = db.query(models.ScanEvent).filter(models.ScanEvent.overall_rating <= 2).all()
        added = 0
        for scan in scans:
            existing = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.scan_event_id == scan.id).first()
            if not existing:
                new_fb = models.NegativeFeedback(
                    business_id=scan.business_id,
                    scan_event_id=scan.id,
                    rating=scan.overall_rating,
                    feedback_text=scan.review_text or f"Customer gave a {scan.overall_rating}-star rating",
                    created_at=scan.scanned_at
                )
                db.add(new_fb)
                added += 1
        
        db.commit()
        print(f"Added {added} missing negative feedbacks from scan events.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_missing_negative_feedbacks()
