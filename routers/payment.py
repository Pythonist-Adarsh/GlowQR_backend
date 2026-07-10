from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
import models, schemas
import os
import time
from datetime import datetime, timezone

router = APIRouter(prefix="/api/payment", tags=["Payment"])

@router.post("/create-order")
def create_payment_order(data: schemas.PaymentOrderCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    merchant_upi_id = os.environ.get("MERCHANT_UPI_ID")
    if not merchant_upi_id:
        raise HTTPException(status_code=500, detail="Merchant UPI ID not configured")
        
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    timestamp = int(time.time())
    tn = f"GLOWQR-{business.id}-{timestamp}"
    
    order = models.PaymentOrder(
        business_id=business.id,
        plan_name=data.plan_name,
        amount=data.amount,
        currency="INR",
        status="pending",
        upi_transaction_note=tn
    )
    
    db.add(order)
    db.commit()
    db.refresh(order)
    
    # Generate deep link
    # upi://pay?pa={MERCHANT_UPI_ID}&pn=GlowQR&am={amount}&cu=INR&tn={upi_transaction_note}
    deep_link = f"upi://pay?pa={merchant_upi_id}&pn=GlowQR&am={data.amount}&cu=INR&tn={tn}"
    
    return {
        "order_id": order.id,
        "upi_transaction_note": tn,
        "deep_link": deep_link,
        "amount": data.amount,
        "merchant_upi_id": merchant_upi_id
    }

@router.post("/submit-utr")
def submit_utr(data: schemas.PaymentOrderSubmitUTR, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    order = db.query(models.PaymentOrder).filter(models.PaymentOrder.id == data.order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business or order.business_id != business.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this order")
        
    if not data.utr_reference or len(data.utr_reference.strip()) < 6:
        raise HTTPException(status_code=400, detail="Invalid UTR reference")
        
    order.utr_reference = data.utr_reference.strip()
    order.status = "utr_submitted"
    order.utr_submitted_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"message": "UTR submitted successfully. We will verify and activate your plan shortly."}
