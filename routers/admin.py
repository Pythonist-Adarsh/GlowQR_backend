from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from database import get_db
import models
import os
from datetime import datetime, timedelta, timezone
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def verify_admin(secret: str = Query(None), x_admin_secret: str = Header(None)):
    admin_secret = os.environ.get("ADMIN_SECRET", "supersecretadmin")
    if secret == admin_secret or x_admin_secret == admin_secret:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/upgrade/approve", response_class=HTMLResponse)
def approve_upgrade(id: int, secret: str = Query(...), db: Session = Depends(get_db)):
    verify_admin(secret=secret)
    req = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.id == id).first()
    if not req:
        return "<html><body><h2>Not found</h2></body></html>"
    if req.status != 'pending':
        return f"<html><body><h2>Already processed ({req.status})</h2></body></html>"
        
    req.status = 'verified'
    req.activated_at = datetime.now(timezone.utc)
    req.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if user:
        user.plan = req.plan_requested
        
    sub = models.Subscription(
        user_id=req.user_id,
        plan=req.plan_requested,
        status='active',
        razorpay_subscription_id=f'manual_{id}',
        current_period_start=datetime.now(timezone.utc),
        current_period_end=datetime.now(timezone.utc) + timedelta(days=30),
        amount_paise=req.amount_paid
    )
    db.add(sub)
    db.commit()
    
    return f"<html><body><h2>✅ Done!</h2><p>{user.email} upgraded to {user.plan}. Valid until {req.expires_at}</p></body></html>"

@router.get("/upgrade/reject", response_class=HTMLResponse)
def reject_upgrade(id: int, secret: str = Query(...), reason: str = None, db: Session = Depends(get_db)):
    verify_admin(secret=secret)
    req = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.id == id).first()
    if not req:
        return "<html><body><h2>Not found</h2></body></html>"
    if req.status != 'pending':
        return f"<html><body><h2>Already processed ({req.status})</h2></body></html>"
        
    req.status = 'rejected'
    req.admin_note = reason
    db.commit()
    return "<html><body><h2>❌ Rejected.</h2></body></html>"

@router.get("/upgrade/pending")
def get_pending_upgrades(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    reqs = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.status == 'pending').all()
    return {
        "requests": reqs,
        "count": len(reqs)
    }

@router.get("/users")
def get_users(plan: str = 'all', limit: int = 20, offset: int = 0, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    query = db.query(models.User)
    if plan != 'all':
        query = query.filter(models.User.plan == plan)
        
    total = query.count()
    users = query.offset(offset).limit(limit).all()
    return {"users": users, "total": total}

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    from sqlalchemy import func
    total_users = db.query(models.User).count()
    
    plans = db.query(models.User.plan, func.count(models.User.id)).group_by(models.User.plan).all()
    by_plan = {p: c for p, c in plans}
    
    total_scans_today = db.query(models.ScanEvent).filter(models.ScanEvent.scanned_at >= datetime.now(timezone.utc).date()).count()
    
    first_of_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total_scans_this_month = db.query(models.ScanEvent).filter(models.ScanEvent.scanned_at >= first_of_month).count()
    
    pending_upgrades = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.status == 'pending').count()
    
    revenue = db.query(func.sum(models.UpgradeRequest.amount_paid)).filter(
        models.UpgradeRequest.status == 'verified',
        models.UpgradeRequest.activated_at >= first_of_month
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "by_plan": by_plan,
        "total_scans_today": total_scans_today,
        "total_scans_this_month": total_scans_this_month,
        "pending_upgrade_requests": pending_upgrades,
        "total_revenue_this_month": revenue / 100
    }
