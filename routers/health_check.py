from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import math
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
        
    results = autocomplete_search(search_query, req.session_token)
    return results

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0 # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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
    
    if cat_lower == "restaurant":
        included_types = ["restaurant"]
        radius = 1500.0
    elif cat_lower == "food court":
        included_types = ["food_court"]
        radius = 1500.0
    elif cat_lower == "cafe":
        included_types = ["cafe"]
        radius = 1500.0
    elif cat_lower == "salon":
        included_types = ["beauty_salon"]
        radius = 2000.0
    elif cat_lower == "gym":
        included_types = ["gym"]
        radius = 3000.0
    elif cat_lower == "ca firm":
        included_types = ["accounting"]
        radius = 5000.0
    elif cat_lower == "real estate":
        included_types = ["real_estate_agency"]
        radius = 5000.0
    elif cat_lower == "bakery":
        included_types = ["bakery"]
        radius = 3000.0
    elif cat_lower == "jewellery store":
        included_types = ["jewelry_store"]
        radius = 4000.0
    elif cat_lower == "boutique":
        included_types = ["clothing_store"]
        radius = 4000.0
    elif cat_lower == "dental clinic":
        included_types = ["dental_clinic"]
        radius = 2000.0
    elif cat_lower == "medical clinic":
        included_types = ["medical_clinic"]
        radius = 2000.0
    elif cat_lower == "hotel":
        included_types = ["hotel"]
        radius = 3000.0
    elif cat_lower == "coaching institute":
        included_types = ["school"]
        radius = 4000.0
    elif cat_lower == "automobile service":
        included_types = ["car_repair"]
        radius = 5000.0
    else:
        included_types = ["store"]
        radius = 3000.0
        
    scoring_competitors_raw = []
    city_wide_competitors_raw = []
    if lat and lng:
        scoring_competitors_raw = fetch_nearby_competitors(lat, lng, radius, included_types)
        city_wide_competitors_raw = fetch_nearby_competitors(lat, lng, 15000.0, included_types)
    
    # Filter out the target itself if it appears in competitor list by ID
    scoring_competitors = [c for c in scoring_competitors_raw if c.get("id") != req.place_id]
    
    # Sort competitors by review count and take top 8 for scoring
    scoring_competitors.sort(key=lambda x: x.get("userRatingCount", 0), reverse=True)
    scoring_competitors = scoring_competitors[:8]
    
    comp_reviews = [c.get("userRatingCount", 0) for c in scoring_competitors]
    avg_comp_reviews = int(sum(comp_reviews) / len(comp_reviews)) if comp_reviews else 0
    top_comp_reviews = max(comp_reviews) if comp_reviews else 0
    
    # Calculate local radius
    footfall_cats = ["bakery", "cafe", "restaurant", "salon", "gym", "food court", "boutique"]
    local_radius_km = 2.5 if any(f in cat_lower for f in footfall_cats) else 6.0
    
    # Generate local competitors list
    local_competitors_list = []
    for c in scoring_competitors_raw:
        if c.get("id") == req.place_id:
            continue
        c_lat = c.get("location", {}).get("latitude")
        c_lng = c.get("location", {}).get("longitude")
        dist = None
        if lat and lng and c_lat and c_lng:
            dist = haversine(lat, lng, c_lat, c_lng)
        
        if dist is not None and dist <= local_radius_km:
            local_competitors_list.append({
                "name": c.get("displayName", {}).get("text", "Unknown"),
                "rating": c.get("rating", 0),
                "reviews": c.get("userRatingCount", 0),
                "distance_km": round(dist, 1)
            })
            
    local_competitors_list.sort(key=lambda x: x["reviews"], reverse=True)
    local_competitors_list = local_competitors_list[:8]
    
    # Generate city-wide competitors list
    city_competitors_list = []
    for c in city_wide_competitors_raw:
        if c.get("id") == req.place_id:
            continue
        c_lat = c.get("location", {}).get("latitude")
        c_lng = c.get("location", {}).get("longitude")
        dist = None
        if lat and lng and c_lat and c_lng:
            dist = haversine(lat, lng, c_lat, c_lng)
            
        city_competitors_list.append({
            "name": c.get("displayName", {}).get("text", "Unknown"),
            "rating": c.get("rating", 0),
            "reviews": c.get("userRatingCount", 0),
            "distance_km": round(dist, 1) if dist is not None else None
        })
        
    city_competitors_list.sort(key=lambda x: x["reviews"], reverse=True)
    city_competitors_list = city_competitors_list[:8]
    
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
        competitors=city_competitors_list,
        local_competitors=local_competitors_list,
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
