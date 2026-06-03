from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from datetime import datetime, timezone
from database import get_db
from sqlalchemy.orm import Session
from models import User
import os
from dotenv import load_dotenv

load_dotenv()
JWT_SECRET = os.getenv("SECRET_KEY", "supersecretkey")

async def get_current_user(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_email = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.email == user_email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    if user.plan == 'trial' and user.trial_ends_at and user.trial_ends_at < datetime.now(timezone.utc):
        user.plan = 'expired'
        db.commit()
    
    return user

def require_basic(current_user: User = Depends(get_current_user)):
    if current_user.plan not in ['trial', 'basic', 'premium']:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "plan_required",
                "required_plan": "basic",
                "message": "Upgrade to Basic ₹199/month to access this feature",
                "upgrade_url": "/dashboard/subscription"
            }
        )
    return current_user

def require_premium(current_user: User = Depends(get_current_user)):
    if current_user.plan != 'premium':
        raise HTTPException(
            status_code=403,
            detail={
                "error": "plan_required", 
                "required_plan": "premium",
                "message": "Upgrade to Premium ₹499/month to access this feature",
                "upgrade_url": "/dashboard/subscription"
            }
        )
    return current_user
