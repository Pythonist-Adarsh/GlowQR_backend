from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from pydantic import BaseModel
from datetime import datetime, timezone

router = APIRouter(prefix="/api/renewal", tags=["Renewal"])

from routers.auth import get_current_user

import os
import requests
import hmac
import hashlib
import base64
from fastapi import Request

class CashfreeOrderRequest(BaseModel):
    plan: str
    amount_paid: int
    billing_cycle: str = "monthly"

@router.post("/cashfree/create-order")
def create_cashfree_order(data: CashfreeOrderRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    business_name = business.name if business else "Unknown Business"
    
    new_request = models.UpgradeRequest(
        user_id=current_user.id,
        business_name=business_name,
        contact_name=current_user.full_name or "Unknown",
        phone=current_user.phone or "Unknown",
        email=current_user.email,
        plan_requested=data.plan,
        billing_cycle=data.billing_cycle,
        amount_paid=data.amount_paid,
        status="pending",
        request_type="renewal",
        payment_method="cashfree"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    client_id = os.environ.get("CASHFREE_CLIENT_ID", "")
    client_secret = os.environ.get("CASHFREE_CLIENT_SECRET", "")
    env = os.environ.get("CASHFREE_ENV", "TEST")
    
    base_url = "https://sandbox.cashfree.com/pg" if env == "TEST" else "https://api.cashfree.com/pg"
    
    frontend_url = os.environ.get("FRONTEND_URL", "https://glowqr.com").rstrip('/')
    
    payload = {
        "order_amount": data.amount_paid,
        "order_currency": "INR",
        "order_id": f"GQ-{new_request.id}",
        "customer_details": {
            "customer_id": f"CUST_{current_user.id}",
            "customer_email": current_user.email or "no-email@example.com",
            "customer_phone": current_user.phone or "9999999999",
            "customer_name": current_user.full_name or "Unknown User"
        },
        "order_meta": {
            "return_url": f"{frontend_url}/payment-success?order_id=GQ-{new_request.id}"
        }
    }
    
    headers = {
        "x-client-id": client_id,
        "x-client-secret": client_secret,
        "x-api-version": "2023-08-01",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(f"{base_url}/orders", json=payload, headers=headers)
        response.raise_for_status()
        cf_data = response.json()
        return {"payment_session_id": cf_data.get("payment_session_id"), "order_id": f"GQ-{new_request.id}"}
    except Exception as e:
        db.delete(new_request)
        db.commit()
        print(f"Cashfree order error: {e}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        raise HTTPException(status_code=500, detail="Failed to create payment order")

@router.post("/cashfree/webhook")
async def cashfree_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    timestamp = request.headers.get('x-webhook-timestamp')
    signature = request.headers.get('x-webhook-signature')
    
    if not timestamp or not signature:
        raise HTTPException(status_code=400, detail="Missing webhook headers")
        
    client_secret = os.environ.get("CASHFREE_CLIENT_SECRET", "")
    
    message = timestamp.encode('utf-8') + raw_body
    expected_sig = base64.b64encode(hmac.new(client_secret.encode('utf-8'), message, hashlib.sha256).digest()).decode('utf-8')
    
    if signature != expected_sig:
        raise HTTPException(status_code=401, detail="Invalid signature")
        
    data = await request.json()
    
    if data.get("type") == "PAYMENT_SUCCESS_WEBHOOK":
        order_info = data.get("data", {}).get("order", {})
        order_id_str = order_info.get("order_id")
        
        if order_id_str and order_id_str.startswith("GQ-"):
            try:
                req_id = int(order_id_str.split("-")[1])
                upgrade_req = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.id == req_id).first()
                if upgrade_req and upgrade_req.status == "pending":
                    from services.subscription_service import activate_subscription_from_request
                    activate_subscription_from_request(upgrade_req, db)
            except Exception as e:
                print(f"Error processing webhook: {e}")
                
    return {"status": "ok"}

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
