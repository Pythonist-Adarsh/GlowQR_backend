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

def plan_gate(required_plan: str):
    plan_hierarchy = {"expired": 0, "basic": 1, "premium": 2, "trial": 3}
    required = {"basic": 1, "premium": 2}
    
    async def check(current_user: User = Depends(get_current_user)):
        if plan_hierarchy.get(current_user.plan, 0) >= required.get(required_plan, 0):
            return current_user
        raise HTTPException(
            status_code=403,
            detail={
                "error": "plan_required",
                "required_plan": required_plan,
                "current_plan": current_user.plan,
                "upgrade_url": "/upgrade"
            }
        )
    return check
