import sys
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from models import UpgradeRequest, Subscription

def fix_revenue_amounts():
    db = SessionLocal()
    try:
        # Let's fix UpgradeRequests
        requests = db.query(UpgradeRequest).filter(
            UpgradeRequest.amount_paid.in_([399, 999, 3999])
        ).all()
        
        print("Fixing UpgradeRequests:")
        for req in requests:
            print(f"ID: {req.id}, Plan: {req.plan_requested}, Amount: {req.amount_paid} -> {req.amount_paid * 100}")
            req.amount_paid = req.amount_paid * 100
            
        # Let's fix Subscriptions
        subs = db.query(Subscription).filter(
            Subscription.amount_paise.in_([399, 999, 3999])
        ).all()
        
        print("Fixing Subscriptions:")
        for sub in subs:
            print(f"ID: {sub.id}, Plan: {sub.plan}, Amount: {sub.amount_paise} -> {sub.amount_paise * 100}")
            sub.amount_paise = sub.amount_paise * 100
            
        # Also need to fix that one subscription that got messed up (it should be 39900 now)
        messed_up_subs = db.query(Subscription).filter(
            Subscription.amount_paise > 1000000
        ).all()
        for sub in messed_up_subs:
            print(f"Fixing messed up Subscription ID: {sub.id}, Plan: {sub.plan}, Amount: {sub.amount_paise} -> 39900")
            sub.amount_paise = 39900
            
        db.commit()
        print("Data fix completed successfully.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_revenue_amounts()
