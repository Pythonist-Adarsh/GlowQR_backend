from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import models, schemas, security as security_auth
from database import get_db
from dependencies import get_current_user
import hashlib
import secrets

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    hashed_password = security_auth.get_password_hash(user.password)
    
    trial_end = datetime.now(timezone.utc) + timedelta(days=3)
    new_user = models.User(
        email=user.email, 
        hashed_password=hashed_password, 
        full_name=user.full_name,
        plan="trial",
        trial_ends_at=trial_end
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = security_auth.create_access_token(data={"sub": new_user.email})
    refresh_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    
    new_rt = models.RefreshToken(
        user_id=new_user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(new_rt)
    db.commit()
    
    return {
        "user": new_user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "onboarding_completed": False
    }

@router.post("/login", response_model=schemas.Token)
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not security_auth.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    
    business = db.query(models.Business).filter(models.Business.owner_id == user.id).first()
    has_business = business is not None and business.is_onboarded
    
    access_token = security_auth.create_access_token(data={"sub": user.email})
    refresh_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    new_rt = models.RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(new_rt)
    db.commit()
    
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer", 
        "onboarding_completed": has_business
    }

@router.post("/refresh", response_model=schemas.RefreshTokenResponse)
def refresh_token(request: schemas.RefreshTokenRequest, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    rt_record = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    
    if not rt_record or rt_record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")
    
    user = db.query(models.User).filter(models.User.id == rt_record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
        
    db.delete(rt_record)
    
    access_token = security_auth.create_access_token(data={"sub": user.email})
    new_refresh_token = secrets.token_hex(32)
    new_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    
    new_rt = models.RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30)
    )
    db.add(new_rt)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
def logout(request: schemas.RefreshTokenRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    rt_record = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == token_hash).first()
    if rt_record:
        db.delete(rt_record)
        db.commit()
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=schemas.AuthMeResponse)
def get_me(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.plan in ['basic', 'premium']:
        sub = db.query(models.Subscription).filter(
            models.Subscription.user_id == current_user.id, 
            models.Subscription.status == 'active'
        ).first()
        if sub and sub.current_period_end < datetime.now(timezone.utc):
            current_user.plan = 'expired'
            sub.status = 'completed'
            db.commit()

    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "plan": current_user.plan,
            "trial_ends_at": current_user.trial_ends_at,
            "current_period_end": sub.current_period_end if 'sub' in locals() and sub else None,
            "avatar_url": current_user.avatar_url
        },
        "business": {
            "id": business.id,
            "name": business.name,
            "slug": business.slug,
            "is_onboarded": business.is_onboarded,
            "onboarding_step": business.onboarding_step,
            "logo_url": business.logo_url,
            "primary_color": business.primary_color
        } if business else None
    }
