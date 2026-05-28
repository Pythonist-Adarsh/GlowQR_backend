import os
from fastapi import FastAPI, Depends, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse, JSONResponse
from database import engine, get_db
import models, security
from middleware.rate_limit import setup_rate_limiting

# Import routers
from routers.auth import router as auth_router
from routers.onboarding import router as onboarding_router
from routers.business import router as business_router
from routers.business import api_router as business_api_router
from routers.scan import router as scan_router
from routers.analytics import router as analytics_router
from routers.upgrade import router as upgrade_router
from routers.admin import router as admin_router

load_dotenv(override=True)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="GlowQR API")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    err_msg = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    print(err_msg)
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": err_msg})

# Rate Limiting
setup_rate_limiting(app)

# CORS
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

# Session Middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "supersecret"))

# Include Routers
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(business_router)
app.include_router(business_api_router)
app.include_router(scan_router)
app.include_router(analytics_router)
app.include_router(upgrade_router)
app.include_router(admin_router)

# Google OAuth Setup
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

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "database": str(e)}

@app.get("/auth/google")
async def google_login(request: Request):
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        email = user_info.get('email')
        google_id = user_info.get('sub')
        full_name = user_info.get('name')

        user = db.query(models.User).filter(
            (models.User.email == email) | (models.User.google_id == google_id)
        ).first()

        if not user:
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
            user.google_id = google_id
            db.commit()
            db.refresh(user)

        business = db.query(models.Business).filter(models.Business.owner_id == user.id).first()
        has_business = business is not None and business.is_onboarded

        access_token = security.create_access_token(data={"sub": user.email})
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/auth-success?token={access_token}&onboarding_completed={str(has_business).lower()}")
        
    except Exception as e:
        print(f"OAuth Error: {str(e)}")
        raise HTTPException(status_code=401, detail="Could not authenticate with Google")
