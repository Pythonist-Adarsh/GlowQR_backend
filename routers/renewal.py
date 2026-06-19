from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/api/renewal", tags=["Renewal"])

from routers.auth import get_current_user

class RenewalRequestData(BaseModel):
    plan: str
    utr_number: str
    amount_paid: int
    payment_method: str

@router.post("/request")
def request_renewal(data: RenewalRequestData, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    business_name = business.name if business else "Unknown Business"
    
    new_request = models.UpgradeRequest(
        user_id=current_user.id,
        business_name=business_name,
        contact_name=current_user.full_name or "Unknown",
        phone=current_user.phone or "Unknown",
        email=current_user.email,
        plan_requested=data.plan,
        amount_paid=data.amount_paid,
        utr_number=data.utr_number,
        payment_method=data.payment_method,
        status="pending",
        request_type="renewal"
    )
    
    db.add(new_request)
    db.commit()
    return {"success": True, "message": "Renewal request submitted"}

@router.get("/status")
def get_renewal_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    
    plan_expires_at = current_user.plan_expires_at
    
    is_expired = False
    days_remaining = 0
    is_expiring_soon = False
    
    if plan_expires_at:
        if plan_expires_at < now:
            is_expired = True
        else:
            diff = plan_expires_at - now
            days_remaining = diff.days
            if days_remaining <= 7:
                is_expiring_soon = True

    # Check QR active status
    qr_active = False
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if business:
        qr_codes = db.query(models.QRCode).filter(models.QRCode.business_id == business.id).all()
        if qr_codes:
            qr_active = all(qr.is_active for qr in qr_codes)
        else:
            qr_active = True # No QR codes yet
            
    # Check pending renewal requests
    pending_renewal = db.query(models.UpgradeRequest).filter(
        models.UpgradeRequest.user_id == current_user.id,
        models.UpgradeRequest.status == "pending",
        models.UpgradeRequest.request_type == "renewal"
    ).first() is not None

    return {
        "plan": current_user.plan,
        "plan_expires_at": plan_expires_at.isoformat() if plan_expires_at else None,
        "days_remaining": days_remaining,
        "is_expiring_soon": is_expiring_soon,
        "is_expired": is_expired,
        "qr_active": qr_active,
        "pending_renewal": pending_renewal
    }
