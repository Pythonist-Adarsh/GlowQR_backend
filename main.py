import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Any
import models, schemas, auth, database
from database import engine, get_db
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
from fastapi import Request
import re
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="GlowQR API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:3050",
        "https://glowqr-frontend.vercel.app",
        "https://glowqr-frontend-git-main-adarshs-projects-c0267937.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Session Middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY"))

# OAuth Setup
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@app.get("/")
async def root():
    return {"message": "Welcome to GlowQR API"}

from sqlalchemy import text

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Try to perform a simple query to verify DB connection
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": str(e)}

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        throw_exception(status.HTTP_400_BAD_REQUEST, "Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    
    # 7 day trial
    trial_end = datetime.utcnow() + timedelta(days=7)
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
    
    # Create token for immediate login
    access_token = auth.create_access_token(data={"sub": new_user.email})
    
    return {
        "user": new_user,
        "access_token": access_token,
        "token_type": "bearer",
        "onboarding_completed": False
    }

@app.post("/login", response_model=schemas.Token)
def login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_credentials.email).first()
    if not user or not auth.verify_password(user_credentials.password, user.hashed_password):
        throw_exception(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    
    # Check if user has a business
    has_business = db.query(models.Business).filter(models.Business.owner_id == user.id).first() is not None
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer", "onboarding_completed": has_business}

# Helper function for exceptions
def throw_exception(status_code: int, detail: str):
    raise HTTPException(status_code=status_code, detail=detail)

# Google OAuth Implementation
@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            throw_exception(status.HTTP_400_BAD_REQUEST, "Failed to get user info from Google")
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        full_name = user_info.get('name')

        # Check if user exists
        user = db.query(models.User).filter(
            (models.User.email == email) | (models.User.google_id == google_id)
        ).first()

        if not user:
            # Register new OAuth user
            user = models.User(
                email=email,
                google_id=google_id,
                full_name=full_name,
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        elif not user.google_id:
            # Link Google account to existing email account
            user.google_id = google_id
            db.commit()
            db.refresh(user)

        # Check if user has completed onboarding
        has_business = db.query(models.Business).filter(models.Business.owner_id == user.id).first() is not None

        # Create JWT token
        access_token = auth.create_access_token(data={"sub": user.email})
        
        # Redirect to frontend with token
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth-success?token={access_token}&onboarding_completed={str(has_business).lower()}")
        
    except Exception as e:
        print(f"OAuth Error: {str(e)}")
        throw_exception(status.HTTP_401_UNAUTHORIZED, "Could not authenticate with Google")

# Business Management Endpoints
def generate_slug(name: str):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

@app.post("/businesses/", response_model=schemas.Business)
def create_business(business: schemas.BusinessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Check if slug already exists, if so append random string or increment
    base_slug = business.slug or generate_slug(business.name)
    slug = base_slug
    counter = 1
    while db.query(models.Business).filter(models.Business.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    new_business = models.Business(
        **business.dict(exclude={"slug"}),
        slug=slug,
        owner_id=current_user.id
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return new_business

@app.get("/businesses/me", response_model=List[schemas.Business])
def get_my_businesses(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    return db.query(models.Business).filter(models.Business.owner_id == current_user.id).all()

@app.get("/businesses/{slug}", response_model=schemas.Business)
def get_business_by_slug(slug: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.slug == slug).first()
    if not business:
        throw_exception(status.HTTP_404_NOT_FOUND, "Business not found")
    return business

# API Endpoints matching Frontend Spec

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def api_register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)

@app.post("/api/auth/login", response_model=schemas.Token)
def api_login_user(user_credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    return login_user(user_credentials, db)

@app.post("/api/onboarding/extract-menu")
def extract_menu(request: schemas.MenuExtractRequest):
    # Mock AI Extraction with rich structure expected by frontend
    return {
        "highlightDishes": "Paneer Tikka\nButter Chicken\nGarlic Naan\nDal Makhani",
        "signatureDish": "Special Butter Chicken",
        "menuCategories": [
          {
            "category": "Starters",
            "items": [
              { "id": 11, "name": "Paneer Tikka", "emoji": "🧀", "price": "₹240" },
              { "id": 12, "name": "Crispy Corn", "emoji": "🌽", "price": "₹180" },
              { "id": 13, "name": "Veg Spring Rolls", "emoji": "🌯", "price": "₹160" }
            ]
          },
          {
            "category": "Mains",
            "items": [
              { "id": 14, "name": "Special Butter Chicken", "emoji": "🍗", "price": "₹380" },
              { "id": 15, "name": "Dal Makhani Premium", "emoji": "🍲", "price": "₹290" },
              { "id": 16, "name": "Garlic Butter Naan", "emoji": "🫓", "price": "₹80" }
            ]
          },
          {
            "category": "Desserts",
            "items": [
              { "id": 17, "name": "Royal Gulab Jamun", "emoji": "🧁", "price": "₹120" },
              { "id": 18, "name": "Mango Kulfi", "emoji": "🍧", "price": "₹140" }
            ]
          }
        ],
        "menuItems": [
          { "id": 11, "name": "Paneer Tikka", "emoji": "🧀" },
          { "id": 12, "name": "Butter Chicken", "emoji": "🍗" }
        ]
    }

@app.get("/api/qr/{slug}")
def get_qr_page_data(slug: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.slug == slug).first()
    if not business:
        throw_exception(status.HTTP_404_NOT_FOUND, "Business not found")
        
    owner = db.query(models.User).filter(models.User.id == business.owner_id).first()
    plan = owner.plan if owner else "trial"
    if plan == "trial" and owner.trial_ends_at and datetime.utcnow() > owner.trial_ends_at:
        plan = "expired"
        
    return {
        "businessName": business.name,
        "tagline": business.tagline or "",
        "brandColor": business.primary_color,
        "logoUrl": business.logo_url,
        "address": business.address or "",
        "plan": plan,
        "googleReviewUrl": business.google_review_url or "",
        "menuItems": business.menu_data or [],
        "businessCategory": business.category or "",
        "negativeFilterEnabled": business.negative_filter_enabled,
        "reviewLanguage": business.review_language,
        "aiVariantCount": int(business.ai_variant_count) if business.ai_variant_count else 3,
        "welcomeMessage": business.welcome_message or "",
        "animationStyle": business.animation_style,
        "seasonalTheme": business.seasonal_theme,
        "qrSlug": business.slug
    }

@app.post("/api/scan/record")
def record_scan(record: schemas.ScanRecordCreate, db: Session = Depends(get_db)):
    new_scan = models.ScanEvent(
        business_id=record.business_id,
        device_type=record.device_type
    )
    db.add(new_scan)
    db.commit()
    return {"status": "success"}

@app.post("/api/scan/feedback")
def submit_feedback(feedback: schemas.FeedbackSubmitCreate, db: Session = Depends(get_db)):
    new_feedback = models.NegativeFeedback(
        business_id=feedback.business_id,
        rating=feedback.rating,
        feedback_text=feedback.feedback_text
    )
    db.add(new_feedback)
    db.commit()
    return {"status": "success"}

@app.post("/api/scan/generate-review")
def generate_review(request: schemas.ReviewGenerationRequest):
    # Mock AI generation
    return {
        "reviews": [
            "Had a great time, highly recommend!",
            "Excellent service and wonderful atmosphere.",
            "Loved the experience, will definitely be back.",
            "Really good value and friendly staff.",
            "A must-visit spot in the city."
        ][:5] # Limit based on frontend request logic
    }

from fastapi import Body

@app.patch("/api/business/profile")
def update_profile(updates: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    business_id = updates.get("id")
    if not business_id:
        throw_exception(status.HTTP_400_BAD_REQUEST, "Business ID required")
        
    business = db.query(models.Business).filter(models.Business.id == business_id, models.Business.owner_id == current_user.id).first()
    if not business:
        throw_exception(status.HTTP_404_NOT_FOUND, "Business not found")
        
    for key, value in updates.items():
        if hasattr(business, key) and key != "id":
            setattr(business, key, value)
            
    db.commit()
    db.refresh(business)
    return business

@app.post("/api/payments/create-subscription")
def create_subscription(sub: schemas.SubscriptionCreate, current_user: models.User = Depends(auth.get_current_user)):
    # Mock Razorpay
    return {
        "subscriptionId": f"sub_mock_{sub.plan}_{current_user.id}",
        "razorpayKeyId": "rzp_test_mock_key"
    }

@app.post("/api/payments/verify")
def verify_payment(response: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    # Mock Verify
    current_user.plan = "premium" # or basic depending on subscription logic
    db.commit()
    return {"status": "success", "plan": current_user.plan}

@app.post("/api/webhooks/razorpay")
def razorpay_webhook(request: Request):
    return {"status": "received"}
