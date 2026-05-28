from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from dependencies import get_current_user, plan_gate
import models, schemas
from datetime import datetime, timedelta, timezone
from services.groq_service import generate_business_insights

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/summary")
def get_summary(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    plan = current_user.plan
    if plan == "expired":
        return {"plan": "expired", "message": "Upgrade to view analytics"}
        
    total_scans = db.query(models.ScanEvent).filter(models.ScanEvent.business_id == business.id).count()
    
    if plan == "trial":
        trial_days_left = (current_user.trial_ends_at - datetime.now(timezone.utc)).days if current_user.trial_ends_at else 0
        reviews_this_week = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == business.id,
            models.ScanEvent.stage == 'posted',
            models.ScanEvent.scanned_at > datetime.now(timezone.utc) - timedelta(days=7)
        ).count()
        return {
            "plan": "trial",
            "trial_days_left": max(trial_days_left, 0),
            "total_scans": total_scans,
            "reviews_this_week": reviews_this_week,
            "scans_last_7_days": [],
            "google_rating": business.google_rating
        }
        
    if plan in ["basic", "premium"]:
        total_redirects = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == business.id,
            models.ScanEvent.stage != 'scanned'
        ).count()
        
        conversion_rate = round(total_redirects / total_scans * 100, 1) if total_scans > 0 else 0
        reviews_this_month = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == business.id,
            models.ScanEvent.stage == 'posted',
            models.ScanEvent.scanned_at > datetime.now(timezone.utc) - timedelta(days=30)
        ).count()
        
        resp = {
            "plan": plan,
            "total_scans": total_scans,
            "total_redirects": total_redirects,
            "conversion_rate": conversion_rate,
            "reviews_this_month": reviews_this_month,
            "scans_last_30_days": [], 
            "redirects_last_30_days": [],
            "top_menu_items": [],
            "ratings_split": {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
        }
        
        if plan == "premium":
            resp.update({
                "heatmap": [],
                "funnel": {},
                "rating_by_category": {},
                "worst_time_slots": [],
                "negative_alerts_count": 0,
                "negative_alerts": []
            })
            
        return resp

@router.get("/ai-insights")
async def get_ai_insights(db: Session = Depends(get_db), current_user: models.User = Depends(plan_gate("premium"))):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    scan_count = db.query(models.ScanEvent).filter(
        models.ScanEvent.business_id == business.id,
        models.ScanEvent.scanned_at > datetime.now(timezone.utc) - timedelta(days=90)
    ).count()
    
    if scan_count < 10:
        return {"insights": [], "reason": "not_enough_data", "min_required": 10}
        
    data = {
        "name": business.name,
        "category": business.category,
        "city": business.city,
        "avg_overall": 4.2,
        "avg_food": 4.5,
        "avg_service": 3.8,
        "avg_atmosphere": 4.1,
        "worst_slots": [],
        "negative_keywords": ["slow", "cold"],
        "top_items": ["Burger", "Fries"],
        "scan_to_open": 65,
        "open_to_copy": 40
    }
    
    insights = await generate_business_insights(data)
    return {"insights": insights, "generated_at": datetime.now(timezone.utc).isoformat(), "data_range": "last 90 days"}

@router.get("/heatmap")
def get_heatmap(days: int = 30, db: Session = Depends(get_db), current_user: models.User = Depends(plan_gate("premium"))):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    results = db.query(
        models.ScanEvent.day_of_week, 
        models.ScanEvent.hour_of_day, 
        func.count(models.ScanEvent.id).label('count')
    ).filter(
        models.ScanEvent.business_id == business.id,
        models.ScanEvent.scanned_at > datetime.now(timezone.utc) - timedelta(days=days),
        models.ScanEvent.day_of_week.isnot(None),
        models.ScanEvent.hour_of_day.isnot(None)
    ).group_by(models.ScanEvent.day_of_week, models.ScanEvent.hour_of_day).all()
    
    return {"heatmap": [{"day_of_week": r.day_of_week, "hour_of_day": r.hour_of_day, "count": r.count} for r in results]}

@router.get("/funnel")
def get_funnel(db: Session = Depends(get_db), current_user: models.User = Depends(plan_gate("premium"))):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    results = db.query(
        models.ScanEvent.stage, 
        func.count(models.ScanEvent.id).label('count')
    ).filter(
        models.ScanEvent.business_id == business.id,
        models.ScanEvent.scanned_at > datetime.now(timezone.utc) - timedelta(days=30)
    ).group_by(models.ScanEvent.stage).all()
    
    total = sum(r.count for r in results)
    funnel = {}
    for r in results:
        funnel[r.stage] = {"count": r.count, "pct": round(r.count / total * 100, 1) if total > 0 else 0}
        
    return {"funnel": funnel}

@router.get("/negative-alerts")
def get_negative_alerts(unread_only: bool = False, limit: int = 20, offset: int = 0, db: Session = Depends(get_db), current_user: models.User = Depends(plan_gate("premium"))):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    query = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.business_id == business.id)
    
    if unread_only:
        query = query.filter(models.NegativeFeedback.is_read == False)
        
    total = query.count()
    alerts = query.order_by(models.NegativeFeedback.created_at.desc()).offset(offset).limit(limit).all()
    return {"alerts": alerts, "total": total}

@router.patch("/negative-alerts/{alert_id}")
def update_negative_alert(alert_id: int, updates: dict, db: Session = Depends(get_db), current_user: models.User = Depends(plan_gate("premium"))):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    alert = db.query(models.NegativeFeedback).filter(models.NegativeFeedback.id == alert_id, models.NegativeFeedback.business_id == business.id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if "is_read" in updates:
        alert.is_read = updates["is_read"]
    if "is_resolved" in updates:
        alert.is_resolved = updates["is_resolved"]
        if alert.is_resolved:
            alert.resolved_at = datetime.now(timezone.utc)
            
    db.commit()
    db.refresh(alert)
    return {"alert": alert}
