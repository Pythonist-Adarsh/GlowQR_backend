from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Body
from sqlalchemy.orm import Session
from database import get_db
from dependencies import get_current_user, plan_gate
import models, schemas
import secrets
import os
from services.storage_service import upload_logo_to_cloudinary

router = APIRouter(prefix="/businesses", tags=["Business"])
api_router = APIRouter(prefix="/api/business", tags=["API Business"])

@router.post("/", response_model=schemas.Business)
def create_business(business: schemas.BusinessCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    import re
    base_slug = business.slug or re.sub(r'[^a-z0-9]+', '-', business.name.lower()).strip('-')
    slug = base_slug
    counter = 1
    while db.query(models.Business).filter(models.Business.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    new_business = models.Business(
        **business.model_dump(exclude={"slug"}),
        slug=slug,
        owner_id=current_user.id
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return new_business

@router.get("/me", response_model=list[schemas.Business])
def get_my_businesses(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return db.query(models.Business).filter(models.Business.owner_id == current_user.id).all()

@router.get("/{slug}", response_model=schemas.Business)
def get_business_by_slug(slug: str, db: Session = Depends(get_db)):
    business = db.query(models.Business).filter(models.Business.slug == slug).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business

@api_router.patch("/profile")
def update_profile(updates: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business_id = updates.get("id")
    if not business_id:
        business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    else:
        business = db.query(models.Business).filter(models.Business.id == business_id, models.Business.owner_id == current_user.id).first()
        
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    for key, value in updates.items():
        if hasattr(business, key) and key != "id":
            setattr(business, key, value)
            
    db.commit()
    db.refresh(business)
    return business

@api_router.post("/logo")
async def update_logo(logo: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    contents = await logo.read()
    url = await upload_logo_to_cloudinary(contents, business.id)
    if url:
        business.logo_url = url
        db.commit()
        return {"logo_url": url}
    raise HTTPException(status_code=500, detail="Failed to upload logo")

@api_router.get("/qr-codes")
def get_qr_codes(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        return {"qr_codes": []}
    
    qrs = db.query(models.QRCode).filter(models.QRCode.business_id == business.id).all()
    return {"qr_codes": [
        {
            "id": q.id,
            "slug": q.slug,
            "label": q.label,
            "is_active": q.is_active,
            "scan_url": f"{os.environ.get('FRONTEND_URL', 'https://glowqr-frontend.vercel.app').rstrip('/')}/r/{q.slug}",
            "qr_image_url": q.qr_image_url,
            "created_at": q.created_at
        } for q in qrs
    ]}

@api_router.post("/qr-codes")
async def create_qr_code(data: schemas.QRCodeCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    import qrcode
    import io
    
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    existing_count = db.query(models.QRCode).filter(models.QRCode.business_id == business.id, models.QRCode.is_active == True).count()
    if current_user.plan == 'basic' and existing_count >= 1:
        raise HTTPException(status_code=403, detail="Basic plan allows max 1 QR code")
    if current_user.plan in ['premium', 'trial'] and existing_count >= 5:
        raise HTTPException(status_code=403, detail="Plan allows max 5 QR codes")
        
    slug = secrets.token_hex(5)
    qr = models.QRCode(business_id=business.id, slug=slug, label=data.label)
    db.add(qr)
    db.commit()
    db.refresh(qr)
    
    # Generate QR Code image automatically
    scan_url = f"{os.environ.get('FRONTEND_URL', 'https://glowqr-frontend.vercel.app').rstrip('/')}/r/{qr.slug}"
    qr_img = qrcode.make(scan_url)
    img_byte_arr = io.BytesIO()
    qr_img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()
    
    # Upload to Cloudinary
    url = await upload_logo_to_cloudinary(img_bytes, f"qr_{business.id}_{qr.id}")
    if url:
        qr.qr_image_url = url
        db.commit()
    
    return {"qr_code": {
        "id": qr.id,
        "slug": qr.slug,
        "label": qr.label,
        "is_active": qr.is_active,
        "scan_url": scan_url,
        "qr_image_url": qr.qr_image_url
    }}

@api_router.post("/qr-codes/{qr_id}/image")
async def upload_qr_image(qr_id: int, image: UploadFile = File(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    qr = db.query(models.QRCode).filter(models.QRCode.id == qr_id, models.QRCode.business_id == business.id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR Code not found")
        
    contents = await image.read()
    url = await upload_logo_to_cloudinary(contents, f"qr_{business.id}_{qr.id}")
    if url:
        qr.qr_image_url = url
        db.commit()
        return {"qr_image_url": url}
    raise HTTPException(status_code=500, detail="Failed to upload QR image")

@api_router.delete("/qr-codes/{qr_id}")
def delete_qr_code(qr_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    business = db.query(models.Business).filter(models.Business.owner_id == current_user.id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    qr = db.query(models.QRCode).filter(models.QRCode.id == qr_id, models.QRCode.business_id == business.id).first()
    if not qr:
        raise HTTPException(status_code=404, detail="QR Code not found")
        
    qr.is_active = False
    db.commit()
    return {"message": "QR deactivated"}
