from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Cookie
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
import models, schemas
import os
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
from fastapi.responses import HTMLResponse, Response
from services.email_service import send_activation_email, send_rejection_email

router = APIRouter(prefix="/api/admin", tags=["Admin"])

def verify_admin(
    secret: str = Query(None), 
    x_admin_secret: str = Header(None),
    admin_session: str = Cookie(None)
):
    admin_secret = os.environ.get("ADMIN_SECRET", "supersecretadmin")
    if secret == admin_secret or x_admin_secret == admin_secret or admin_session == admin_secret:
        return True
    raise HTTPException(status_code=401, detail="Unauthorized")

@router.get("/stats")
def get_stats(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    now = datetime.now(timezone.utc)
    
    total_users = db.query(models.User).count()
    active_subs = db.query(models.Subscription).filter(
        models.Subscription.status == 'active',
        models.Subscription.current_period_end > now
    ).count()
    trial_users = db.query(models.User).filter(
        models.User.plan == 'trial',
        models.User.trial_ends_at > now
    ).count()
    expired_users = db.query(models.User).filter(
        (models.User.plan == 'expired') | (models.User.trial_ends_at <= now)
    ).count()

    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_this_month = db.query(func.sum(models.UpgradeRequest.amount_paid)).filter(
        models.UpgradeRequest.status == 'verified',
        models.UpgradeRequest.activated_at >= first_of_month
    ).scalar() or 0

    pending_requests = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.status == 'pending').count()

    # User signups (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    signups = db.query(
        func.date(models.User.created_at).label('date'), 
        func.count(models.User.id)
    ).filter(models.User.created_at >= thirty_days_ago).group_by(func.date(models.User.created_at)).all()
    signups_chart = [{"date": str(d), "users": c} for d, c in signups]

    # Plan distribution
    plan_dist = db.query(models.User.plan, func.count(models.User.id)).group_by(models.User.plan).all()
    plan_chart = [{"name": p, "value": c} for p, c in plan_dist]

    # Daily revenue (last 30 days)
    daily_rev = db.query(
        func.date(models.UpgradeRequest.activated_at).label('date'),
        func.sum(models.UpgradeRequest.amount_paid)
    ).filter(
        models.UpgradeRequest.status == 'verified',
        models.UpgradeRequest.activated_at >= thirty_days_ago
    ).group_by(func.date(models.UpgradeRequest.activated_at)).all()
    rev_chart = [{"date": str(d), "revenue": c/100 if c else 0} for d, c in daily_rev]

    return {
        "stats": {
            "total_users": total_users,
            "active_subscriptions": active_subs,
            "trial_users": trial_users,
            "expired_users": expired_users,
            "revenue_this_month": revenue_this_month / 100,
            "pending_requests": pending_requests
        },
        "charts": {
            "signups": signups_chart,
            "plan_distribution": plan_chart,
            "daily_revenue": rev_chart
        }
    }

@router.get("/requests")
def get_upgrade_requests(status: str = 'all', db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    query = db.query(models.UpgradeRequest)
    if status != 'all':
        query = query.filter(models.UpgradeRequest.status == status)
    
    reqs = query.order_by(models.UpgradeRequest.created_at.desc()).all()
    return {"requests": reqs}

@router.patch("/upgrade/{id}/approve")
def approve_upgrade_patch(id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    req = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Request already processed ({req.status})")
        
    req.status = 'verified'
    now = datetime.now(timezone.utc)
    req.activated_at = now
    req.expires_at = now + timedelta(days=30)
    
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if user:
        user.plan = req.plan_requested
        
    sub = models.Subscription(
        user_id=req.user_id,
        plan=req.plan_requested,
        status='active',
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
        amount_paise=req.amount_paid
    )
    db.add(sub)
    db.commit()
    
    if user:
        send_activation_email(user, req.business_name, req.plan_requested, req.expires_at)
    
    return {"message": "Approved successfully", "expires_at": req.expires_at}

@router.patch("/upgrade/{id}/reject")
def reject_upgrade_patch(id: int, reason: dict, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    req = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.id == id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != 'pending':
        raise HTTPException(status_code=400, detail=f"Request already processed ({req.status})")
        
    req.status = 'rejected'
    req.admin_note = reason.get('reason', 'No reason provided')
    db.commit()
    
    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    if user:
        send_rejection_email(user, req.business_name, req.admin_note)
        
    return {"message": "Rejected successfully"}

@router.get("/users")
def get_users_list(plan: str = 'all', search: str = '', city: str = 'all', db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    query = db.query(models.User, models.Business).outerjoin(models.Business, models.User.id == models.Business.owner_id)
    
    if plan != 'all':
        query = query.filter(models.User.plan == plan)
    if city != 'all':
        query = query.filter(models.Business.city == city)
    if search:
        search = f"%{search}%"
        query = query.filter(
            (models.User.email.ilike(search)) |
            (models.User.full_name.ilike(search)) |
            (models.Business.name.ilike(search))
        )
        
    results = query.all()
    
    users_data = []
    for user, business in results:
        users_data.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "plan": user.plan,
            "trial_ends_at": user.trial_ends_at,
            "created_at": user.created_at,
            "business": {
                "name": business.name if business else None,
                "category": business.category if business else None,
                "city": business.city if business else None
            }
        })
        
    return {"users": users_data}

@router.get("/users/{id}")
def get_user_details(id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    business = db.query(models.Business).filter(models.Business.owner_id == id).first()
    
    scans_count = 0
    if business:
        scans_count = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business.id).count()
        
    upgrade_history = db.query(models.UpgradeRequest).filter(models.UpgradeRequest.user_id == id).all()
    subs_history = db.query(models.Subscription).filter(models.Subscription.user_id == id).all()
    
    return {
        "user": user,
        "business": business,
        "scans_count": scans_count,
        "upgrade_history": upgrade_history,
        "subs_history": subs_history
    }

@router.patch("/users/{id}/plan")
def update_user_plan(id: int, data: schemas.AdminUserPlanUpdate, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.plan = data.plan
    if data.expires_at and data.plan == 'trial':
        user.trial_ends_at = data.expires_at
    
    db.commit()
    return {"message": "Plan updated"}

@router.delete("/users/{id}")
def delete_user(id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

@router.get("/revenue")
def get_revenue_data(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    now = datetime.now(timezone.utc)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    first_of_last_month = (first_of_month - timedelta(days=1)).replace(day=1)
    
    this_month = db.query(func.sum(models.UpgradeRequest.amount_paid)).filter(
        models.UpgradeRequest.status == 'verified',
        models.UpgradeRequest.activated_at >= first_of_month
    ).scalar() or 0
    
    last_month = db.query(func.sum(models.UpgradeRequest.amount_paid)).filter(
        models.UpgradeRequest.status == 'verified',
        models.UpgradeRequest.activated_at >= first_of_last_month,
        models.UpgradeRequest.activated_at < first_of_month
    ).scalar() or 0
    
    all_time = db.query(func.sum(models.UpgradeRequest.amount_paid)).filter(
        models.UpgradeRequest.status == 'verified'
    ).scalar() or 0
    
    basic_count = db.query(models.Subscription).filter(
        models.Subscription.plan == 'basic',
        models.Subscription.status == 'active',
        models.Subscription.current_period_end > now
    ).count()
    
    premium_count = db.query(models.Subscription).filter(
        models.Subscription.plan == 'premium',
        models.Subscription.status == 'active',
        models.Subscription.current_period_end > now
    ).count()
    
    transactions = db.query(models.UpgradeRequest).filter(
        models.UpgradeRequest.status == 'verified'
    ).order_by(models.UpgradeRequest.activated_at.desc()).limit(100).all()
    
    return {
        "summary": {
            "this_month": this_month / 100,
            "last_month": last_month / 100,
            "all_time": all_time / 100,
            "mrr": (basic_count * 299) + (premium_count * 699),
            "basic_count": basic_count,
            "premium_count": premium_count
        },
        "transactions": transactions
    }

@router.get("/revenue/export")
def export_revenue(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    transactions = db.query(models.UpgradeRequest).filter(
        models.UpgradeRequest.status == 'verified'
    ).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Business Name', 'Plan', 'Amount (Rs)', 'UTR', 'Activated At', 'Expires At'])
    for t in transactions:
        cw.writerow([
            t.id, t.business_name, t.plan_requested, t.amount_paid/100 if t.amount_paid else 0, 
            t.utr_number, t.activated_at, t.expires_at
        ])
        
    return Response(content=si.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=revenue.csv"})

@router.get("/feedback")
def get_negative_feedback(status: str = 'all', business: str = '', db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    query = db.query(models.NegativeFeedback, models.Business).join(models.Business, models.NegativeFeedback.business_id == models.Business.id)
    
    if status == 'unread':
        query = query.filter(models.NegativeFeedback.is_read == False)
    elif status == 'read':
        query = query.filter(models.NegativeFeedback.is_read == True)
    elif status == 'resolved':
        query = query.filter(models.NegativeFeedback.is_resolved == True)
        
    if business:
        query = query.filter(models.Business.name.ilike(f"%{business}%"))
        
    results = query.order_by(models.NegativeFeedback.created_at.desc()).all()
    
    feedbacks = []
    for fb, bus in results:
        fbd = fb.__dict__.copy()
        fbd['business_name'] = bus.name
        fbd.pop('_sa_instance_state', None)
        feedbacks.append(fbd)
        
    stats = {
        "total": db.query(models.NegativeFeedback).count(),
        "unread": db.query(models.NegativeFeedback).filter(models.NegativeFeedback.is_read == False).count(),
        "one_star": db.query(models.NegativeFeedback).filter(models.NegativeFeedback.rating == 1).count(),
        "two_star": db.query(models.NegativeFeedback).filter(models.NegativeFeedback.rating == 2).count()
    }
    
    return {"feedbacks": feedbacks, "stats": stats}

@router.patch("/feedback/{id}")
def update_feedback(id: int, action: dict, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    fb = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.id == id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
        
    if action.get('mark_read') is True:
        fb.is_read = True
    if action.get('mark_resolved') is True:
        fb.is_resolved = True
        fb.resolved_at = datetime.now(timezone.utc)
        
    db.commit()
    return {"message": "Updated"}

@router.get("/settings", response_model=schemas.AdminSettingsResponse)
def get_settings(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.patch("/settings", response_model=schemas.AdminSettingsResponse)
def update_settings(data: schemas.AdminSettingsUpdate, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    settings = db.query(models.AdminSettings).first()
    if not settings:
        settings = models.AdminSettings()
        db.add(settings)
        
    for key, value in data.dict(exclude_unset=True).items():
        setattr(settings, key, value)
        
    db.commit()
    db.refresh(settings)
    return settings
