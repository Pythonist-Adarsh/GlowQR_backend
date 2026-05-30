from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user
import models, schemas
import re
import secrets
import json
from services.storage_service import upload_logo_to_cloudinary
from services.groq_service import extract_menu_from_image
from services.email_service import send_qr_is_live
from typing import Optional

router = APIRouter(prefix="/api/onboarding", tags=["Onboarding"])

@router.get("/status")
def get_status(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        return {"is_onboarded": False, "current_step": 0, "business": None}
    
    return {
        "is_onboarded": business.is_onboarded,
        "current_step": business.onboarding_step,
        "business": business
    }

@router.post("/step/1")
def step_1(data: schemas.OnboardingStep1, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    
    if not business:
        business = models.Business(owner_id=current_user.id)
        db.add(business)
        db.flush()
        
    slug = business.slug
    if not slug:
        base = re.sub(r'[^a-z0-9]+', '-', data.name.lower()).strip('-')
        slug = f"{base}-{secrets.token_hex(3)}"
        
    business.name = data.name
    business.tagline = data.tagline
    business.google_review_url = data.google_review_url
    business.place_id = data.place_id
    business.google_rating = data.google_rating
    business.review_count = data.review_count
    business.slug = slug
    business.onboarding_step = max(business.onboarding_step, 1)
    
    if data.website:
        if not business.menu_data:
            business.menu_data = {}
        # Ensure it is a dict
        if isinstance(business.menu_data, dict):
            business.menu_data["website"] = data.website

    qr_code = db.query(models.QRCode).filter(models.QRCode.business_id == business.id).first()
    if not qr_code:
        new_qr = models.QRCode(business_id=business.id, slug=slug, label='Main QR', is_active=True)
        db.add(new_qr)
        
    db.commit()
    db.refresh(business)
    return {"business": business, "qr_slug": slug}

@router.post("/step/2")
async def step_2(
    city: Optional[str] = Form(None),
    area_locality: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None),
    owner_email: Optional[str] = Form(None),
    opening_time: Optional[str] = Form("09:00"),
    closing_time: Optional[str] = Form("22:00"),
    days_open: Optional[str] = Form(None),
    primary_color: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Must complete step 1 first")
        
    try:
        days_open_list = json.loads(days_open) if days_open else ["Mon","Tue","Wed","Thu","Fri","Sat"]
    except:
        days_open_list = ["Mon","Tue","Wed","Thu","Fri","Sat"]
        
    business_hours_json = {
        "opening": opening_time,
        "closing": closing_time,
        "days": days_open_list
    }
    
    logo_url = business.logo_url
    if logo:
        contents = await logo.read()
        url = await upload_logo_to_cloudinary(contents, business.id)
        if url:
            logo_url = url
            
    business.city = city
    business.area_locality = area_locality
    business.address = address
    business.phone_number = phone_number
    business.whatsapp_number = whatsapp_number
    business.owner_email = owner_email or current_user.email
    business.business_hours = business_hours_json
    if primary_color:
        business.primary_color = primary_color
    business.logo_url = logo_url
    business.onboarding_step = max(business.onboarding_step, 2)
    
    db.commit()
    db.refresh(business)
    return {"business": business, "logo_url": logo_url}

@router.post("/step/3")
def step_3(data: schemas.OnboardingStep3, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    valid_categories = ['restaurant', 'cafe', 'fastfood', 'bar', 'bakery', 'foodcourt']
    if data.category.lower() not in valid_categories:
        raise HTTPException(status_code=422, detail="Invalid category")
        
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    business.category = data.category
    business.price_range = data.price_range
    business.cuisine_speciality = data.cuisine_speciality
    business.dietary_options = data.dietary_options
    business.onboarding_step = max(business.onboarding_step, 3)
    db.commit()
    db.refresh(business)
    return {"business": business}

@router.post("/step/4")
def step_4(data: schemas.OnboardingStep4, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Please complete Step 1 first")
    business.signature_dish = data.signature_dish
    business.highlighted_dishes = data.highlighted_dishes
    business.excluded_dishes = data.excluded_dishes
    
    if data.menu_categories is not None:
        business.menu_data = data.menu_categories
        
        # Sync menu items table
        db.query(models.MenuItem).filter(models.MenuItem.business_id == business.id).delete()
        
        idx = 0
        for category in data.menu_categories:
            items = category.get('items', [])
            for item in items:
                new_item = models.MenuItem(
                    business_id=business.id,
                    name=item.get('name'),
                    is_active=True,
                    sort_order=idx
                )
                db.add(new_item)
                idx += 1
                
    business.onboarding_step = max(business.onboarding_step, 4)
    db.commit()
    db.refresh(business)
    return {"business": business, "menu_items_count": db.query(models.MenuItem).filter(models.MenuItem.business_id == business.id).count()}

@router.post("/step/5")
async def step_5(
    theme: Optional[str] = Form(None),
    primary_color: Optional[str] = Form(None),
    welcome_msg: Optional[str] = Form(None),
    variants: Optional[str] = Form(None),
    language: Optional[str] = Form("English"),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if current_user.plan == 'expired':
        raise HTTPException(status_code=403, detail={"error": "plan_expired", "upgrade_url": "/upgrade"})
        
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=400, detail="Please complete Step 1 first")
    
    animation_style = 'glow_float'
    if current_user.plan == 'basic':
        animation_style = 'glow_float'
    else:
        if theme == 'classic': animation_style = 'particle_burst'
        elif theme == 'premium': animation_style = 'minimal_fade'
        
    ai_variant_count = 3
    if variants:
        try:
            ai_variant_count = int(variants.split()[0])
        except:
            pass
    if current_user.plan == 'basic':
        ai_variant_count = min(ai_variant_count, 3)
        
    db_language = language.lower()
    if db_language not in ["english", "hindi", "hinglish"]:
        db_language = "english"
        
    logo_url = business.logo_url
    if logo:
        contents = await logo.read()
        url = await upload_logo_to_cloudinary(contents, business.id)
        if url:
            logo_url = url
            
    business.animation_style = animation_style
    business.primary_color = primary_color or business.primary_color
    business.welcome_message = welcome_msg
    business.ai_variant_count = ai_variant_count
    business.review_language = db_language
    business.logo_url = logo_url
    business.onboarding_step = max(business.onboarding_step, 5)
    
    db.commit()
    db.refresh(business)
    return {
        "business": business,
        "logo_url": logo_url,
        "animation_style": animation_style,
        "ai_variant_count": ai_variant_count
    }

@router.post("/complete")
async def complete_onboarding(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    
    required = {
        "name": business.name,
        "google_review_url": business.google_review_url,
        "owner_email": business.owner_email
    }
    missing = [k for k,v in required.items() if not v]
    if missing:
        raise HTTPException(status_code=400, detail={"error": "missing_required_fields", "fields": missing, "message": "Please complete steps 1 and 2 first"})
        
    business.is_onboarded = True
    business.onboarding_step = 6
    db.commit()
    
    qr_code = db.query(models.QRCode).filter(models.QRCode.business_id == business.id, models.QRCode.is_active == True).first()
    scan_url = f"https://glowqr-frontend.vercel.app/r/{qr_code.slug}" if qr_code else ""
    
    if qr_code and not qr_code.qr_image_url:
        import qrcode
        import io
        qr_img = qrcode.make(scan_url)
        img_byte_arr = io.BytesIO()
        qr_img.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        url = await upload_logo_to_cloudinary(img_bytes, f"qr_{business.id}_{qr_code.id}")
        if url:
            qr_code.qr_image_url = url
            db.commit()
    
    try:
        send_qr_is_live(business.name, business.owner_email, scan_url)
    except Exception as e:
        print(f"Error sending email: {e}")
        
    return {
        "success": True,
        "business": business,
        "qr_code": {
            "id": qr_code.id,
            "slug": qr_code.slug,
            "label": qr_code.label,
            "scan_url": scan_url,
            "is_active": qr_code.is_active,
            "qr_image_url": qr_code.qr_image_url if qr_code else None
        } if qr_code else None
    }

@router.post("/extract-menu")
async def extract_menu(file: UploadFile = File(...)):
    file_bytes = await file.read()
    menu_data = await extract_menu_from_image(file_bytes, file.content_type)
    return menu_data
