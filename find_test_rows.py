import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import UpgradeRequest, Subscription

def find_test_rows():
    db = SessionLocal()
    try:
        # Find UpgradeRequests for House of Aadayein
        requests = db.query(UpgradeRequest).filter(
            UpgradeRequest.business_name == "House of Aadayein",
            UpgradeRequest.status == "verified"
        ).order_by(UpgradeRequest.created_at.asc()).all()
        
        print("Duplicate/Test UpgradeRequests for House of Aadayein:")
        for req in requests:
            print(f"ID: {req.id}, Date: {req.created_at}, Plan: {req.plan_requested}, Amount (paise): {req.amount_paid}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    find_test_rows()
