from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request, Cookie, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from pydantic import BaseModel
import models, schemas
import os
import csv
from io import StringIO
from datetime import datetime, timedelta, timezone
from fastapi.responses import HTMLResponse, Response
from services.email_service import send_activation_email, send_rejection_email
from sqlalchemy import Integer, desc

router = APIRouter(prefix="/api/admin", tags=["Admin"])

@router.post("/sync-now")
def trigger_sync_now(x_admin_key: str = Header(None)):
    # Fallback to a hardcoded key if env var isn't set, for safety
    expected_key = os.environ.get("ADMIN_API_KEY", "super-secret-admin-key")
    if x_admin_key != expected_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    from jobs.daily_sync import sync_all_businesses
    return sync_all_businesses()

import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", "super-secret-admin-jwt-key")
ALGORITHM = "HS256"

def verify_admin(admin_session: str = Cookie(None)):
    if not admin_session:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        payload = jwt.decode(admin_session, ADMIN_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="Unauthorized")
        return True
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Unauthorized")

@router.post("/login")
def admin_login(data: schemas.AdminLoginRequest, response: Response, db: Session = Depends(get_db)):
    settings = db.query(models.AdminSettings).first()
    if not settings or not settings.admin_email or not settings.admin_password_hash:
        raise HTTPException(status_code=500, detail="Admin account not configured")
        
    if data.email != settings.admin_email:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    if not pwd_context.verify(data.password, settings.admin_password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    token = jwt.encode(
        {"sub": "admin", "exp": datetime.utcnow() + timedelta(hours=24)}, 
        ADMIN_JWT_SECRET, 
        algorithm=ALGORITHM
    )
    
    response.set_cookie(
        key="admin_session",
        value=token,
        httponly=True,
        max_age=86400,
        samesite="lax",
        path="/"
    )
    return {"success": True, "token": token}

@router.patch("/change-password")
def change_password(data: schemas.AdminChangePasswordRequest, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    settings = db.query(models.AdminSettings).first()
    if not settings:
        raise HTTPException(status_code=500, detail="Admin account not configured")
        
    if not pwd_context.verify(data.current_password, settings.admin_password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
        
    settings.admin_password_hash = pwd_context.hash(data.new_password)
    db.commit()
    return {"success": True, "message": "Password updated"}

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
    
    if req.billing_cycle == 'yearly':
        req.expires_at = now + timedelta(days=365)
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
            from services.email_service import send_renewal_confirmed_alert
            send_renewal_confirmed_alert(
                owner_email=user.email,
                owner_name=user.full_name or "User",
                plan=user.plan,
                new_expiry_date=req.expires_at.strftime("%B %d, %Y")
            )
        else:
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
    query = query.filter(models.User.account_status != 'trashed')
    
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
            "mrr": (basic_count * 199) + (premium_count * 499),
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

@router.post("/run-daily-sync")
async def trigger_daily_sync(
    background_tasks: BackgroundTasks,
    x_admin_secret: str = Header(...)
):
    admin_secret = os.getenv("ADMIN_SECRET", "supersecretadmin")
    if x_admin_secret != admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    from jobs.daily_sync import run_daily_sync
    background_tasks.add_task(run_daily_sync)
    return {"message": "Daily sync started in background"}

@router.get("/top-businesses")
def get_top_businesses(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    results = db.query(
        models.Business,
        models.User.plan,
        func.count(models.ScanEvent.id).label("total_scans"),
        func.sum(func.cast(models.ScanEvent.redirected_to_google, Integer)).label("google_redirects")
    ).outerjoin(models.ScanEvent, models.ScanEvent.business_id == models.Business.id)\
     .outerjoin(models.User, models.User.id == models.Business.owner_id)\
     .group_by(models.Business.id, models.User.plan)\
     .order_by(desc("total_scans"))\
     .limit(10)\
     .all()
    
    top = []
    for rank, (bus, plan, total_scans, google_redirects) in enumerate(results, start=1):
        total_scans = total_scans or 0
        google_redirects = google_redirects or 0
        redirect_rate = (google_redirects / total_scans * 100) if total_scans > 0 else 0
        top.append({
            "id": bus.id,
            "rank": rank,
            "name": bus.name,
            "category": bus.category,
            "city": bus.city,
            "plan": plan or "trial",
            "total_scans": total_scans,
            "google_redirects": google_redirects,
            "redirect_rate_percent": round(redirect_rate, 1)
        })
    return {"top_businesses": top}

@router.get("/business/{business_id}/detail")
def get_business_admin_detail(business_id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    bus = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not bus:
        raise HTTPException(status_code=404, detail="Business not found")
        
    usr = db.query(models.User).filter(models.User.id == bus.owner_id).first()
    
    business_info = {
        "name": bus.name,
        "slug": bus.slug,
        "category": bus.category,
        "city": bus.city,
        "area": bus.area_locality,
        "address": bus.address,
        "phone": bus.phone_number,
        "owner_email": bus.owner_email,
        "owner_name": usr.full_name if usr else None,
        "owner_phone": usr.phone if usr else None,
        "plan": usr.plan if usr else "trial",
        "trial_ends_at": usr.trial_ends_at if usr else None,
        "google_rating": bus.google_rating,
        "google_review_count": bus.review_count,
        "baseline_review_count": bus.baseline_review_count,
        "place_id": bus.place_id,
        "google_review_url": bus.google_review_url,
        "tagline": bus.tagline,
        "created_at": bus.created_at,
        "is_onboarded": bus.is_onboarded,
        "negative_filter_enabled": bus.negative_filter_enabled,
        "whatsapp_alerts": usr.whatsapp_alerts if usr else False,
        "notif_negative_alert": usr.notif_negative_alert if usr else False
    }

    total_scans = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id).count()
    redirects = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.redirected_to_google == True).count()
    reviews_generated = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.review_text.isnot(None)).count()
    negative_scans = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.was_negative == True).count()
    
    avg_rating_row = db.query(func.avg(models.ScanEvent.overall_rating), func.avg(models.ScanEvent.time_spent_seconds)).filter(models.ScanEvent.business_id == business_id).first()
    avg_overall_rating = avg_rating_row[0] if avg_rating_row and avg_rating_row[0] else 0
    avg_time_spent = avg_rating_row[1] if avg_rating_row and avg_rating_row[1] else 0

    now = datetime.now(timezone.utc)
    scans_last_7 = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.scanned_at > now - timedelta(days=7)).count()
    scans_last_30 = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.scanned_at > now - timedelta(days=30)).count()
    last_scan = db.query(func.max(models.ScanEvent.scanned_at)).filter(models.ScanEvent.business_id == business_id).scalar()

    scan_stats = {
        "total_scans": total_scans,
        "total_google_redirects": redirects,
        "redirect_rate_percent": round((redirects/total_scans*100), 1) if total_scans > 0 else 0,
        "reviews_generated": reviews_generated,
        "reviews_copied_rate": round((reviews_generated/total_scans*100), 1) if total_scans > 0 else 0,
        "avg_overall_rating": round(avg_overall_rating, 1),
        "negative_scans": negative_scans,
        "negative_rate_percent": round((negative_scans/total_scans*100), 1) if total_scans > 0 else 0,
        "avg_time_spent_seconds": round(avg_time_spent, 1),
        "scans_last_7_days": scans_last_7,
        "scans_last_30_days": scans_last_30,
        "last_scan_at": last_scan
    }

    rating_counts = db.query(models.ScanEvent.overall_rating, func.count(models.ScanEvent.id)).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.overall_rating.isnot(None)).group_by(models.ScanEvent.overall_rating).all()
    rd_dict = {f"{r}_star": 0 for r in range(1, 6)}
    for r, c in rating_counts:
        rd_dict[f"{r}_star"] = c

    hour_counts = db.query(models.ScanEvent.hour_of_day, func.count(models.ScanEvent.id)).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.hour_of_day.isnot(None)).group_by(models.ScanEvent.hour_of_day).order_by(desc(func.count(models.ScanEvent.id))).limit(5).all()
    peak_hours = [{"hour": h, "scan_count": c} for h, c in hour_counts]

    day_counts = db.query(models.ScanEvent.day_of_week, func.count(models.ScanEvent.id)).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.day_of_week.isnot(None)).group_by(models.ScanEvent.day_of_week).all()
    peak_days = [{"day": d, "scan_count": c} for d, c in day_counts]

    all_selected = db.query(models.ScanEvent.selected_items).filter(models.ScanEvent.business_id == business_id, models.ScanEvent.selected_items.isnot(None)).all()
    from collections import Counter
    item_tally = Counter()
    for row in all_selected:
        if row[0]:
            for item in row[0]:
                item_tally[item] += 1
    top_selected_items = [{"item": k, "count": v} for k, v in item_tally.most_common(5)]

    neg_feedbacks = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.business_id == business_id).all()
    unresolved_neg = sum(1 for nf in neg_feedbacks if not nf.is_resolved)
    last_neg = max((nf.created_at for nf in neg_feedbacks if nf.created_at), default=None)
    
    negative_feedback_summary = {
        "total_negative": len(neg_feedbacks),
        "unresolved": unresolved_neg,
        "last_negative_at": last_neg
    }

    recent_negative = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.business_id == business_id).order_by(models.NegativeFeedback.created_at.desc()).limit(5).all()
    recent_negative_feedback = [{"rating": nf.rating, "feedback_text": nf.feedback_text, "created_at": nf.created_at, "is_resolved": nf.is_resolved} for nf in recent_negative]

    grt = db.query(models.GoogleRatingHistory).filter(models.GoogleRatingHistory.business_id == business_id).order_by(models.GoogleRatingHistory.fetched_at.asc()).all()
    google_rating_trend = [{"rating": g.rating, "review_count": g.review_count, "fetched_at": g.fetched_at} for g in grt]

    da = db.query(models.DailyAnalytics).filter(models.DailyAnalytics.business_id == business_id, models.DailyAnalytics.date >= now - timedelta(days=30)).order_by(models.DailyAnalytics.date.asc()).all()
    daily_scans_chart = [{"date": d.date.strftime("%Y-%m-%d") if d.date else None, "total_scans": d.total_scans, "google_redirects": d.google_redirects} for d in da]

    bomb_alerts = db.query(models.BombAlert).filter(models.BombAlert.business_id == business_id).all()
    unresolved_bombs = sum(1 for ba in bomb_alerts if not ba.is_resolved)
    highest_risk = max((ba.risk_score for ba in bomb_alerts), default=0)
    last_bomb = max((ba.triggered_at for ba in bomb_alerts if ba.triggered_at), default=None)

    bomb_alerts_summary = {
        "total_alerts": len(bomb_alerts),
        "unresolved": unresolved_bombs,
        "highest_risk_score": highest_risk,
        "last_alert_at": last_bomb
    }

    sessions = db.query(models.ScanSession).filter(models.ScanSession.business_id == business_id).all()
    flagged_sessions = sum(1 for s in sessions if s.is_flagged)
    times = [s.time_to_rate_seconds for s in sessions if s.time_to_rate_seconds is not None]
    avg_session_time = sum(times)/len(times) if times else 0

    session_stats = {
        "total_sessions": len(sessions),
        "flagged_sessions": flagged_sessions,
        "avg_time_to_rate": round(avg_session_time, 1)
    }

    return {
        "business_info": business_info,
        "scan_stats": scan_stats,
        "rating_distribution": rd_dict,
        "peak_hours": peak_hours,
        "peak_days": peak_days,
        "top_selected_items": top_selected_items,
        "negative_feedback_summary": negative_feedback_summary,
        "recent_negative_feedback": recent_negative_feedback,
        "google_rating_trend": google_rating_trend,
        "daily_scans_chart": daily_scans_chart,
        "bomb_alerts_summary": bomb_alerts_summary,
        "session_stats": session_stats
    }

@router.get("/trashed-users")
def get_trashed_users_list(search: str = '', db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    query = db.query(models.User, models.Business).outerjoin(models.Business, models.User.id == models.Business.owner_id)
    query = query.filter(models.User.account_status == 'trashed')
    
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
        active_qr_count = 0
        if business:
            active_qr_count = db.query(models.QRCode).filter(
                models.QRCode.business_id == business.id,
                models.QRCode.is_active == True
            ).count()
            
        users_data.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "plan": user.plan,
            "billing_cycle": user.billing_cycle,
            "plan_expires_at": user.plan_expires_at,
            "deleted_at": user.deleted_at,
            "business": {
                "name": business.name if business else None,
                "city": business.city if business else None,
                "category": business.category if business else None,
            },
            "active_qr_count": active_qr_count
        })
        
    return {"users": users_data}

@router.delete("/user/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    usr = db.query(models.User).filter(models.User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")

    usr.account_status = 'trashed'
    from datetime import datetime, timezone
    usr.deleted_at = datetime.now(timezone.utc)
    
    businesses = db.query(models.Business).filter(models.Business.owner_id == user_id).all()
    for b in businesses:
        qr_codes = db.query(models.QRCode).filter(models.QRCode.business_id == b.id).all()
        for qr in qr_codes:
            qr.is_active = False

    db.commit()
    return {"message": "User moved to trash successfully"}

class HardDeleteRequest(BaseModel):
    admin_pin: str

@router.delete("/user/{user_id}/hard")
def hard_delete_user(user_id: int, req: HardDeleteRequest, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    settings = db.query(models.AdminSettings).first()
    from security import verify_password
    if not settings or not verify_password(req.admin_pin, settings.admin_password_hash):
        raise HTTPException(status_code=403, detail="Invalid admin password/PIN")

    usr = db.query(models.User).filter(models.User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")

    bus_ids = [b.id for b in db.query(models.Business.id).filter(models.Business.owner_id == user_id).all()]

    if bus_ids:
        db.query(models.NegativeFeedback).filter(models.NegativeFeedback.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.BombAlert).filter(models.BombAlert.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.ScanSession).filter(models.ScanSession.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.ScanEvent).filter(models.ScanEvent.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.DailyAnalytics).filter(models.DailyAnalytics.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.AIAnalyticsCache).filter(models.AIAnalyticsCache.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.GoogleRatingHistory).filter(models.GoogleRatingHistory.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.MenuItem).filter(models.MenuItem.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.QRCode).filter(models.QRCode.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.OnboardingRecord).filter(models.OnboardingRecord.business_id.in_(bus_ids)).delete(synchronize_session=False)
        db.query(models.Business).filter(models.Business.owner_id == user_id).delete(synchronize_session=False)

    db.query(models.Subscription).filter(models.Subscription.user_id == user_id).delete(synchronize_session=False)
    db.query(models.UpgradeRequest).filter(models.UpgradeRequest.user_id == user_id).delete(synchronize_session=False)
    db.query(models.RefreshToken).filter(models.RefreshToken.user_id == user_id).delete(synchronize_session=False)
    db.query(models.User).filter(models.User.id == user_id).delete(synchronize_session=False)

    db.commit()
    return {"message": "User permanently deleted"}

@router.post("/user/{user_id}/restore")
def restore_user(user_id: int, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    usr = db.query(models.User).filter(models.User.id == user_id).first()
    if not usr:
        raise HTTPException(status_code=404, detail="User not found")
        
    usr.account_status = 'active'
    usr.deleted_at = None
    usr.plan = 'expired'
    
    db.commit()
    
    # Send expired alert to user
    settings = db.query(models.AdminSettings).first()
    upi_id = settings.upi_id if settings else ""
    from services.email_service import send_expired_alert
    try:
        send_expired_alert(owner_email=usr.email, owner_name=usr.full_name or "User", upi_id=upi_id)
    except Exception as e:
        print(f"Failed to send restore/expired alert: {e}")
        
    return {"message": "User restored and marked as expired"}

@router.get("/businesses-list")
def get_businesses_list(db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    results = db.query(models.Business, models.User).join(models.User, models.Business.owner_id == models.User.id).all()
    out = []
    for bus, usr in results:
        out.append({
            "id": bus.id,
            "name": bus.name,
            "category": bus.category,
            "city": bus.city,
            "plan": usr.plan or "trial",
            "primaryColor": bus.primary_color,
            "welcomeMessage": bus.welcome_message,
            "tagline": bus.tagline,
            "logoUrl": bus.logo_url,
            "website": bus.website_url
        })
    return {"businesses": out}

from pydantic import BaseModel
class SimulateReviewsRequest(BaseModel):
    business_name: str
    category: str
    city: str
    services: str
    overall_rating: int
    plan: str

@router.post("/simulate-reviews")
async def simulate_reviews(data: SimulateReviewsRequest, verified: bool = Depends(verify_admin)):
    from services.groq_service import generate_reviews
    services_list = [s.strip() for s in data.services.split(",") if s.strip()]
    
    result = await generate_reviews(
        business_name=data.business_name,
        category=data.category,
        overall_rating=data.overall_rating,
        selected_items=services_list,
        plan=data.plan,
        city=data.city,
        return_debug=True
    )
    
    return result

@router.patch("/business/{business_id}/review-url")
def update_review_url(business_id: int, data: schemas.ReviewUrlUpdate, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    business.place_id = data.place_id
    business.google_review_url = f"https://search.google.com/local/writereview?placeid={data.place_id}"
    db.commit()
    db.refresh(business)
    return {"google_place_id": business.place_id, "google_review_url": business.google_review_url}
