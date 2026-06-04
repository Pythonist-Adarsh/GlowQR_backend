with open('routers/scan.py', 'r', encoding='utf-8') as f:
    data = f.read()

target = """    qr_code = None
    if req.qr_slug and req.qr_slug.lower() != 'onboarding':
        qr_code = db.query(models.QRCode).filter(models.QRCode.slug == req.qr_slug).first()
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR Code not found")
        
    variants = await generate_reviews("""

replacement = """    qr_code = None
    previous_reviews = []
    if req.qr_slug and req.qr_slug.lower() != 'onboarding':
        qr_code = db.query(models.QRCode).filter(models.QRCode.slug == req.qr_slug).first()
        if not qr_code:
            raise HTTPException(status_code=404, detail="QR Code not found")
        
        recent_scans = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == qr_code.business_id,
            models.ScanEvent.review_text.isnot(None)
        ).order_by(models.ScanEvent.scanned_at.desc()).limit(15).all()
        previous_reviews = [s.review_text for s in recent_scans if s.review_text]
        
    variants = await generate_reviews("""

if target in data:
    data = data.replace(target, replacement)
    # Now replace the function call
    call_target = """        plan=req.plan,
        city=req.city
    )"""
    call_replacement = """        plan=req.plan,
        city=req.city,
        previous_reviews=previous_reviews
    )"""
    data = data.replace(call_target, call_replacement)
    with open('routers/scan.py', 'w', encoding='utf-8') as f:
        f.write(data)
    print("Patched scan.py")
else:
    print("Target not found")
