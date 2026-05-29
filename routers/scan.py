from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
import secrets
import hashlib
from datetime import datetime, timezone
from services.groq_service import generate_reviews
from services.email_service import send_negative_feedback_alert

router = APIRouter(tags=["Scan"])

@router.get("/api/qr/{slug}")
def get_qr_page_data(slug: str, db: Session = Depends(get_db)):
    qr_code = db.query(models.QRCode).filter(models.QRCode.slug == slug).first()
    if not qr_code or not qr_code.is_active:
        raise HTTPException(status_code=404, detail="QR Code not found or inactive")
        
    business = db.query(models.Business).filter(models.Business.id == qr_code.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    owner = db.query(models.User).filter(models.User.id == business.owner_id).first()
    plan = owner.plan if owner else "trial"
    if plan == "trial" and owner.trial_ends_at and datetime.now(timezone.utc) > owner.trial_ends_at:
        plan = "expired"
        
    if plan == "expired":
        return {
            "plan": "expired",
            "business_name": business.name,
            "logo_url": business.logo_url
        }
        
    menu_items = [item.name for item in business.menu_items if item.is_active]
        
    return {
        "business_name": business.name,
        "tagline": business.tagline or "",
        "brand_color": business.primary_color,
        "logo_url": business.logo_url,
        "address": business.address or "",
        "city": business.city or "",
        "plan": plan,
        "google_review_url": business.google_review_url or "",
        "menu_items": menu_items,
        "business_category": business.category or "",
        "negative_filter_enabled": business.negative_filter_enabled,
        "review_language": business.review_language,
        "ai_variant_count": business.ai_variant_count or 3,
        "welcome_message": business.welcome_message or "",
        "animation_style": business.animation_style,
        "seasonal_theme": business.seasonal_theme,
        "particle_intensity": business.particle_intensity,
        "qr_slug": slug
    }

@router.post("/api/scan/record")
def record_scan(record: schemas.ScanRecordCreate, request: Request, db: Session = Depends(get_db)):
    qr_code = db.query(models.QRCode).filter(models.QRCode.slug == record.qr_slug).first()
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR Code not found")
        
    if record.stage == 'scanned' and not record.session_id:
        session_id = secrets.token_hex(5)
        ip_hash = hashlib.sha256(request.client.host.encode()).hexdigest() if request.client else None
        user_agent = request.headers.get('user-agent')
        
        new_scan = models.ScanEvent(
            qr_code_id=qr_code.id,
            business_id=qr_code.business_id,
            session_id=session_id,
            stage=record.stage,
            ip_hash=ip_hash,
            user_agent=user_agent,
            device_type=record.device_type
        )
        db.add(new_scan)
        db.commit()
        return {"session_id": session_id, "recorded": True}
    else:
        scan = db.query(models.ScanEvent).filter(models.ScanEvent.session_id == record.session_id).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Session not found")
            
        scan.stage = record.stage
        if record.overall_rating is not None: scan.overall_rating = record.overall_rating
        if record.food_rating is not None: scan.food_rating = record.food_rating
        if record.service_rating is not None: scan.service_rating = record.service_rating
        if record.atmosphere_rating is not None: scan.atmosphere_rating = record.atmosphere_rating
        if record.selected_items is not None: scan.selected_items = record.selected_items
        if record.meal_type is not None: scan.meal_type = record.meal_type
        if record.price_range is not None: scan.price_range = record.price_range
        if record.seating_type is not None: scan.seating_type = record.seating_type
        if record.wait_time is not None: scan.wait_time = record.wait_time
        if record.review_variant is not None: scan.review_variant = record.review_variant
        if record.review_text is not None: scan.review_text = record.review_text
        if record.was_negative is not None: scan.was_negative = record.was_negative
        
        db.commit()
        return {"session_id": record.session_id, "recorded": True}

@router.post("/api/scan/generate-review")
async def generate_review_endpoint(req: schemas.ReviewGenerationRequest, db: Session = Depends(get_db)):
    qr_code = None
    if req.qr_slug and req.qr_slug.lower() != 'onboarding':
        qr_code = db.query(models.QRCode).filter(models.QRCode.slug == req.qr_slug).first()
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR Code not found")
        
    variants = await generate_reviews(
        business_name=req.business_name,
        category=req.category,
        tagline=req.tagline,
        overall_rating=req.overall_rating,
        food_rating=req.food_rating,
        service_rating=req.service_rating,
        atmosphere_rating=req.atmosphere_rating,
        selected_items=req.selected_items,
        signature_dish=req.signature_dish,
        meal_type=req.meal_type,
        price_range=req.price_range,
        language=req.language,
        variant_count=req.variant_count,
        plan=req.plan
    )
    
    return {"variants": variants, "language": req.language}

@router.post("/api/scan/feedback")
def submit_feedback(feedback: schemas.FeedbackSubmitCreate, db: Session = Depends(get_db)):
    qr_code = db.query(models.QRCode).filter(models.QRCode.slug == feedback.qr_slug).first()
    if not qr_code:
        raise HTTPException(status_code=404, detail="QR not found")
        
    business = db.query(models.Business).filter(models.Business.id == qr_code.business_id).first()
    
    scan_id = None
    if feedback.session_id:
        scan = db.query(models.ScanEvent).filter(models.ScanEvent.session_id == feedback.session_id).first()
        if scan:
            scan.was_negative = True
            scan_id = scan.id
            
    new_feedback = models.NegativeFeedback(
        business_id=business.id,
        scan_event_id=scan_id,
        rating=feedback.rating,
        feedback_text=feedback.feedback
    )
    db.add(new_feedback)
    db.commit()
    
    if business.owner_email:
        try:
            send_negative_feedback_alert(business.name, business.owner_email, feedback.rating, feedback.feedback)
        except Exception as e:
            print(f"Failed to send alert email: {e}")
            
    return {"message": "Thank you for your feedback"}
