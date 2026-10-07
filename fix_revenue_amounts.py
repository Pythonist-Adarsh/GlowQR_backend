import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import UpgradeRequest, Subscription

def fix_revenue_amounts():
    db = SessionLocal()
    try:
        # Find all UpgradeRequests where amount_paid is exactly 399 or 999 or 3999 (which are clearly not paise)
        # Or specifically House of Aadayein as requested
        
        # Let's see all UpgradeRequests for House of Aadayein
        requests = db.query(UpgradeRequest).filter(
            UpgradeRequest.business_name == "House of Aadayein"
        ).all()
        
        print("Found UpgradeRequests for House of Aadayein:")
        for req in requests:
            print(f"ID: {req.id}, Date: {req.created_at}, Plan: {req.plan_requested}, Amount: {req.amount_paid}")
            if req.amount_paid in [399, 999, 3999]:
                print(f"  -> Fixing ID {req.id}: {req.amount_paid} -> {req.amount_paid * 100}")
                req.amount_paid = req.amount_paid * 100
                
                # Also fix the corresponding Subscription if it exists and has the incorrect amount
                sub = db.query(Subscription).filter(
                    Subscription.user_id == req.user_id,
                    Subscription.amount_paise == req.amount_paid / 100
                ).first()
                if sub:
                    print(f"  -> Fixing related Subscription ID {sub.id}: {sub.amount_paise} -> {sub.amount_paise * 100}")
                    sub.amount_paise = sub.amount_paise * 100
                    
        db.commit()
        print("Data fix completed successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_revenue_amounts()
