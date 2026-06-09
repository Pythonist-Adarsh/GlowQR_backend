from fastapi import APIRouter, Depends, HTTPException, Cookie, Header, Query
from sqlalchemy.orm import Session
from database import get_db
import models
from dependencies import get_current_user
from routers.admin import verify_admin
from sqlalchemy import desc
from datetime import datetime, timezone, timedelta

router = APIRouter(tags=["BombAlerts"])

def check_premium_plan(business_id: int, user: models.User, db: Session):
    business = db.query(models.Business).filter(models.Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    if business.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    owner = db.query(models.User).filter(models.User.id == business.owner_id).first()
    if not owner or owner.plan != 'premium':
        raise HTTPException(
            status_code=403,
            detail={
                "error": "upgrade_required",
                "message": "Review Bomb Protection is available on the Premium plan only.",
                "upgrade_url": "/pricing"
            }
        )
    return business

@router.get("/api/bomb-alerts/{business_id}")
async def get_bomb_alerts(business_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_premium_plan(business_id, current_user, db)
    
    alerts = db.query(models.BombAlert).filter(models.BombAlert.business_id == business_id).order_by(desc(models.BombAlert.triggered_at)).all()
    
    flagged_count = db.query(models.ScanSession).filter(
        models.ScanSession.business_id == business_id,
        models.ScanSession.is_flagged == True
    ).count()
    
    return {"alerts": alerts, "flagged_count": flagged_count}

@router.get("/api/bomb-alerts/{business_id}/{alert_id}/report")
async def get_bomb_alert_report(business_id: int, alert_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    check_premium_plan(business_id, current_user, db)
    
    alert = db.query(models.BombAlert).filter(models.BombAlert.id == alert_id, models.BombAlert.business_id == business_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if not alert.evidence_report_url:
        raise HTTPException(status_code=404, detail="Report not generated yet")
        
    return {"report_url": alert.evidence_report_url}

@router.patch("/api/bomb-alerts/{alert_id}/resolve")
async def resolve_bomb_alert(
    alert_id: str,
    authorization: str = Header(None),
    admin_session: str = Cookie(None),
    db: Session = Depends(get_db)
):
    is_admin = False
    current_user = None
    
    if admin_session:
        try:
            verify_admin(admin_session)
            is_admin = True
        except Exception:
            pass
            
    if not is_admin and authorization:
        try:
            current_user = await get_current_user(authorization, db)
        except Exception:
            pass
            
    if not is_admin and not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    alert = db.query(models.BombAlert).filter(models.BombAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if not is_admin:
        business = db.query(models.Business).filter(models.Business.id == alert.business_id).first()
        if not business or business.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
    alert.is_resolved = True
    db.commit()
    return {"status": "resolved"}

@router.get("/api/admin/bomb-alerts")
def get_admin_bomb_alerts(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), verified: bool = Depends(verify_admin)):
    alerts = db.query(models.BombAlert, models.Business.name.label('business_name'), models.User.plan)\
        .join(models.Business, models.BombAlert.business_id == models.Business.id)\
        .join(models.User, models.Business.owner_id == models.User.id)\
        .order_by(desc(models.BombAlert.triggered_at))\
        .offset(skip).limit(limit).all()
        
    result = []
    for a, b_name, plan in alerts:
        res = a.__dict__.copy()
        res.pop('_sa_instance_state', None)
        res['business_name'] = b_name
        res['plan'] = plan
        result.append(res)
        
    now = datetime.now(timezone.utc)
    total_attacks_month = db.query(models.BombAlert).filter(
        models.BombAlert.triggered_at >= now - timedelta(days=30),
        models.BombAlert.verdict != 'organic'
    ).count()
    
    businesses_under_attack = db.query(models.BombAlert.business_id).filter(
        models.BombAlert.is_resolved == False,
        models.BombAlert.verdict != 'organic'
    ).distinct().count()
    
    total_flagged_sessions = db.query(models.ScanSession).filter(models.ScanSession.is_flagged == True).count()
    
    return {
        "alerts": result,
        "stats": {
            "total_attacks_this_month": total_attacks_month,
            "businesses_under_attack": businesses_under_attack,
            "total_flagged_sessions": total_flagged_sessions
        }
    }
