from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models
from services.email_service import send_renewal_confirmed_alert, send_activation_email

def activate_subscription_from_request(req: models.UpgradeRequest, db: Session):
    """
    Activates a subscription based on an UpgradeRequest.
    Sets status to verified, updates user, creates Subscription record, activates QRs, and sends emails.
    """
    if req.status != 'pending':
        # Idempotency check: if already processed, don't double-activate.
        return req.expires_at
        
    req.status = 'verified'
    now = datetime.now(timezone.utc)
    req.activated_at = now
    
    if req.billing_cycle == 'yearly':
        req.expires_at = now + timedelta(days=365)
    elif req.billing_cycle == 'quarterly':
        req.expires_at = now + timedelta(days=90)
    else:
        req.expires_at = now + timedelta(days=30)
    
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if user:
        user.plan = req.plan_requested
        user.billing_cycle = req.billing_cycle
        user.plan_expires_at = req.expires_at
        user.renewal_reminder_sent = False
        
        # Activate QR codes
        businesses = db.query(models.Business).filter(models.Business.owner_id == user.id).all()
        for business in businesses:
            qr_codes = db.query(models.QRCode).filter(models.QRCode.business_id == business.id).all()
            for qr in qr_codes:
                qr.is_active = True
        
    sub = models.Subscription(
        user_id=req.user_id,
        plan=req.plan_requested,
        status='active',
        current_period_start=now,
        current_period_end=req.expires_at,
        amount_paise=req.amount_paid
    )
    db.add(sub)
    db.commit()
    
    if user:
        if req.request_type == 'renewal':
            send_renewal_confirmed_alert(
                owner_email=user.email,
                owner_name=user.full_name or "User",
                plan=user.plan,
                new_expiry_date=req.expires_at.strftime("%B %d, %Y")
            )
        else:
            send_activation_email(user, req.business_name, req.plan_requested, req.expires_at)
    
    return req.expires_at
