from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
import models, schemas
import os
from datetime import datetime, timedelta, timezone
from services.email_service import send_upgrade_alert_to_admin

router = APIRouter(prefix="/api/upgrade", tags=["Upgrade"])

@router.post("/request")
def request_upgrade(data: schemas.UpgradeRequestCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    amount_paid = 29900 if data.plan == 'basic' else 69900
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    business_name = business.name if business else "Unknown Business"
    
    upgrade_req = models.UpgradeRequest(
        user_id=current_user.id,
        business_name=business_name,
        contact_name=data.contact_name,
        phone=data.phone,
        email=current_user.email,
        plan_requested=data.plan,
        amount_paid=amount_paid,
        utr_number=data.utr_number,
        payment_method=data.payment_method
    )
    db.add(upgrade_req)
    db.commit()
    db.refresh(upgrade_req)
    
    reference_code = f"GQ-{upgrade_req.id:04d}"
    api_url = os.environ.get("API_URL", "http://localhost:8000")
    admin_secret = os.environ.get("ADMIN_SECRET", "supersecretadmin")
    
    approve_url = f"{api_url}/api/admin/upgrade/approve?id={upgrade_req.id}&secret={admin_secret}"
    reject_url = f"{api_url}/api/admin/upgrade/reject?id={upgrade_req.id}&secret={admin_secret}"
    
    try:
        send_upgrade_alert_to_admin(
            {
                "id": upgrade_req.id,
                "business_name": business_name,
                "contact_name": data.contact_name,
                "phone": data.phone,
                "email": current_user.email,
                "plan_requested": data.plan,
                "utr_number": data.utr_number,
                "payment_method": data.payment_method
            },
            approve_url,
            reject_url
        )
    except Exception as e:
        print(f"Failed to send admin email: {e}")
        
    return {
        "request_id": upgrade_req.id,
        "reference_code": reference_code,
        "message": "Request received. You'll get an email once activated within 2-4 hours."
    }

@router.get("/status")
def get_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    trial_days = None
    if current_user.plan == 'trial' and current_user.trial_ends_at:
        trial_days = max((current_user.trial_ends_at - datetime.now(timezone.utc)).days, 0)
        
    pending = db.query(models.UpgradeRequest).filter(
        models.UpgradeRequest.user_id == current_user.id,
        models.UpgradeRequest.status == 'pending'
    ).order_by(models.UpgradeRequest.created_at.desc()).first()
    
    sub = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.status == 'active'
    ).first()
    
    return {
        "current_plan": current_user.plan,
        "trial_days_left": trial_days,
        "pending_request": {
            "reference_code": f"GQ-{pending.id:04d}",
            "plan_requested": pending.plan_requested,
            "status": pending.status,
            "created_at": pending.created_at.isoformat()
        } if pending else None,
        "active_until": sub.current_period_end.isoformat() if sub else None
    }
