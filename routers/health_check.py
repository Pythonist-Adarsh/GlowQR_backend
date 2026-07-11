from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import HealthCheckScan
from schemas_health import SearchRequest, PlaceResult, ScanRequest, ScanResponse, CaptureLeadRequest, CompetitorData
from services.places_service import autocomplete_search, fetch_place_details, fetch_nearby_competitors
from services.email_service import send_health_report_email
from services.geo_aeo_service import analyze_geo_aeo_signals

router = APIRouter(prefix="/api/health-check", tags=["Health Checker"])

@router.post("/search", response_model=List[PlaceResult])
def search_business(req: SearchRequest):
    search_query = req.query
    
    if req.category:
        search_query += f" {req.category}"
    if req.city:
        search_query += f" {req.city}"
        
    results = autocomplete_search(search_query, req.session_token)
    return results

@router.post("/scan", response_model=ScanResponse)
def run_scan(req: ScanRequest, db: Session = Depends(get_db)):
    # 1. Fetch exact business details
    target_data = fetch_place_details(req.place_id, req.session_token)
    if not target_data:
        raise HTTPException(status_code=404, detail="Could not fetch data for this place.")
        
    rating = target_data.get("rating", 0)
    reviews = target_data.get("userRatingCount", 0)
    
    # Extract lat/lng for Nearby Search
    location = target_data.get("location", {})
    lat = location.get("latitude")
    lng = location.get("longitude")
    
    # 2. Fetch competitors
    # Map category to Google Places type and radius
    cat_lower = req.category.lower()
    radius = 2000.0
    included_types = []
    
    if "restaurant" in cat_lower:
        included_types = ["restaurant"]
        radius = 1500.0
    elif "cafe" in cat_lower:
        included_types = ["cafe", "coffee_shop"]
        radius = 1500.0
    elif "salon" in cat_lower or "spa" in cat_lower:
        included_types = ["beauty_salon", "hair_care", "spa"]
        radius = 2000.0
    elif "gym" in cat_lower or "fitness" in cat_lower:
        included_types = ["gym", "fitness_center"]
        radius = 3000.0
    elif "ca firm" in cat_lower or "accountant" in cat_lower:
        included_types = ["accounting", "finance"]
        radius = 5000.0
    elif "real estate" in cat_lower:
        included_types = ["real_estate_agency"]
        radius = 5000.0
    elif "bakery" in cat_lower:
        included_types = ["bakery"]
        radius = 3000.0
    elif "jewellery" in cat_lower:
        included_types = ["jewelry_store"]
        radius = 4000.0
    elif "boutique" in cat_lower:
        included_types = ["clothing_store"]
        radius = 4000.0
    elif "wellness" in cat_lower or "spa" in cat_lower:
        included_types = ["spa", "massage_clinic"]
        radius = 3000.0
    elif "dental" in cat_lower:
        included_types = ["dental_clinic", "dentist"]
        radius = 2000.0
    elif "medical" in cat_lower:
        included_types = ["medical_clinic", "doctor"]
        radius = 2000.0
    elif "electronics" in cat_lower:
        included_types = ["electronics_store"]
        radius = 4000.0
    elif "furniture" in cat_lower:
        included_types = ["furniture_store"]
        radius = 5000.0
    elif "photography" in cat_lower:
        included_types = ["photography_studio", "photographer"]
        radius = 5000.0
    elif "event planner" in cat_lower:
        included_types = ["event_planner"]
        radius = 5000.0
    elif "hotel" in cat_lower:
        included_types = ["hotel", "guest_house"]
        radius = 3000.0
    elif "coaching" in cat_lower:
        included_types = ["school", "cram_school"]
        radius = 4000.0
    elif "garage" in cat_lower or "automobile" in cat_lower:
        included_types = ["auto_repair", "car_repair"]
        radius = 5000.0
    elif "interior designer" in cat_lower:
        included_types = ["interior_designer"]
        radius = 5000.0
    else:
        included_types = ["store"]
        radius = 3000.0
        
    competitors_raw = []
    if lat and lng:
        competitors_raw = fetch_nearby_competitors(lat, lng, radius, included_types)
    
    # Filter out the target itself if it appears in competitor list by ID
    competitors = [c for c in competitors_raw if c.get("id") != req.place_id]
    
    # Sort competitors by review count and take top 8
    competitors.sort(key=lambda x: x.get("userRatingCount", 0), reverse=True)
    competitors = competitors[:8]
    
    comp_reviews = [c.get("userRatingCount", 0) for c in competitors]
    avg_comp_reviews = int(sum(comp_reviews) / len(comp_reviews)) if comp_reviews else 0
    top_comp_reviews = max(comp_reviews) if comp_reviews else 0
    
    # 3. Calculate Scores
    # GMB Score Logic: 
    # Max 100. 
    # Base 50 based on rating vs 4.0 threshold. 
    # Base 50 based on review count vs competitors.
    
    gmb_score = 0
    
    if rating >= 4.5:
        gmb_score += 50
    elif rating >= 4.0:
        gmb_score += 40
    elif rating >= 3.5:
        gmb_score += 20
    else:
        gmb_score += 10
        
    if top_comp_reviews > 0:
        if reviews >= top_comp_reviews:
            gmb_score += 50
        elif reviews >= avg_comp_reviews:
            gmb_score += 35
        else:
            ratio = (reviews / top_comp_reviews) * 50
            gmb_score += int(ratio)
    else:
        gmb_score += 50 # No competitors found, default to good score on this metric
        
    # Cap at 100
    gmb_score = min(100, gmb_score)
    
    # Placeholders for SEO and GEO/AEO
    seo_score = 0
    geo_aeo_score = 0
    
    # Headline Score (50% GMB, 25% SEO, 25% GEO)
    # Issues
    issues = []
    if rating < 4.0:
        issues.append("Your rating is below the 4.0 trust threshold. Customers may choose competitors.")
    if reviews < avg_comp_reviews:
        issues.append(f"You have {reviews} reviews, but the local average is {avg_comp_reviews}. You are losing visibility.")
    elif reviews < top_comp_reviews:
        issues.append(f"Your top competitor has {top_comp_reviews} reviews. They are likely getting the lion's share of local clicks.")
    
    # 4. GEO/AEO and SEO Analysis
    website_url = target_data.get("websiteUri", "")
    phone = target_data.get("nationalPhoneNumber", "")
    reviews_data = target_data.get("reviews", [])
    
    geo_aeo_result = analyze_geo_aeo_signals(
        website_url=website_url,
        business_name=req.name,
        phone=phone,
        reviews=reviews_data,
        category=req.category
    )
    
    has_website = geo_aeo_result["has_website"]
    geo_aeo_score = geo_aeo_result["geo_aeo_score"]
    geo_aeo_signals = geo_aeo_result["sub_signals"]
    
    for sig in geo_aeo_signals:
        if not sig.get("passed"):
            issues.append(f"AI Search Issue: {sig.get('message')}")
    
    # Placeholder for SEO Score until proper implementation
    seo_score = 0
    if has_website:
        seo_score = 50 # Basic fallback if has website
        
    # Calculate Headline Score
    if has_website:
        headline_score = int((gmb_score * 0.5) + (seo_score * 0.25) + (geo_aeo_score * 0.25))
    else:
        headline_score = gmb_score

    # Save to DB
    scan_record = HealthCheckScan(
        google_place_id=req.place_id,
        business_name=req.name,
        category=req.category,
        city=req.city,
        headline_score=headline_score,
        gmb_score=gmb_score,
        seo_score=seo_score,
        geo_aeo_score=geo_aeo_score,
        competitor_avg_reviews=avg_comp_reviews,
        competitor_top_reviews=top_comp_reviews
    )
    db.add(scan_record)
    db.commit()
    db.refresh(scan_record)
    
    comp_list = [
        CompetitorData(
            name=c.get("displayName", {}).get("text", ""),
            rating=c.get("rating", 0), 
            reviews=c.get("userRatingCount", 0)
        ) 
        for c in competitors
    ]
    
    return ScanResponse(
        scan_id=scan_record.id,
        headline_score=headline_score,
        gmb_score=gmb_score,
        seo_score=seo_score,
        geo_aeo_score=geo_aeo_score,
        business_rating=rating,
        business_reviews=reviews,
        competitor_avg_reviews=avg_comp_reviews,
        competitor_top_reviews=top_comp_reviews,
        competitors=comp_list,
        issues=issues,
        has_website=has_website,
        geo_aeo_signals=geo_aeo_signals
    )

@router.post("/capture-lead")
def capture_lead(req: CaptureLeadRequest, db: Session = Depends(get_db)):
    scan = db.query(HealthCheckScan).filter(HealthCheckScan.id == req.scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
        
    if req.email:
        scan.contact_email = req.email
    if req.phone:
        scan.contact_phone = req.phone
        
    db.commit()
    
    if req.email:
        # Note: PDF generation is a separate follow-up task. 
        # Sending a clean HTML email as an interim solution.
        send_health_report_email(req.email, scan)
        
    return {"status": "success"}
