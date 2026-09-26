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
    cat_lower = req.category.lower().strip()
    radius = 2000.0
    included_types = []
    
    if cat_lower in ["restaurant", "finedining", "fine dining"]:
        included_types = ["restaurant"]
        radius = 1500.0
    elif cat_lower in ["fast food / qsr", "fastfood", "fast food", "food court", "foodcourt", "food truck", "foodtruck"]:
        included_types = ["fast_food_restaurant", "restaurant", "meal_takeaway"]
        radius = 1500.0
    elif cat_lower in ["cafe", "cafe / coffee shop"]:
        included_types = ["cafe", "coffee_shop"]
        radius = 1500.0
    elif cat_lower in ["bar / lounge", "bar", "lounge"]:
        included_types = ["bar"]
        radius = 1500.0
    elif cat_lower in ["cloud kitchen", "cloudkitchen"]:
        included_types = ["meal_delivery", "meal_takeaway"]
        radius = 2000.0
    elif cat_lower in ["salon", "spa", "beauty salon"]:
        included_types = ["beauty_salon", "hair_care", "spa"]
        radius = 2000.0
    elif cat_lower in ["gym", "fitness", "fitness center"]:
        included_types = ["gym", "fitness_center"]
        radius = 3000.0
    elif cat_lower in ["ca firm", "tax / ca firm", "accounting"]:
        included_types = ["accounting"]
        radius = 5000.0
    elif cat_lower in ["real estate", "real_estate", "real estate agency"]:
        included_types = ["real_estate_agency"]
        radius = 5000.0
    elif cat_lower in ["bakery", "bakery / dessert shop"]:
        included_types = ["bakery"]
        radius = 3000.0
    elif cat_lower in ["jewellery", "jewellery store", "bridal & festive jewellery"]:
        included_types = ["jewelry_store"]
        radius = 4000.0
    elif cat_lower in ["boutique", "clothing store"]:
        included_types = ["clothing_store"]
        radius = 4000.0
    elif cat_lower in ["dental clinic"]:
        included_types = ["dental_clinic"]
        radius = 2000.0
    elif cat_lower in ["medical clinic", "medical", "doctor clinic"]:
        included_types = ["medical_clinic", "doctor", "hospital"]
        radius = 2000.0
    elif cat_lower in ["hotel", "motel"]:
        included_types = ["hotel", "lodging"]
        radius = 3000.0
    elif cat_lower in ["coaching institute", "education", "school"]:
        included_types = ["school", "university"]
        radius = 4000.0
    elif cat_lower in ["automobile service", "car repair"]:
        included_types = ["car_repair"]
        radius = 5000.0
    elif cat_lower in ["grocery/general retail", "domestic mart", "retail", "supermarket", "grocery store"]:
        if cat_lower in ["supermarket", "retail"]:
            included_types = ["supermarket", "grocery_store", "convenience_store"]
        else:
            included_types = ["grocery_store", "convenience_store"]
        radius = 3000.0
    else:
        included_types = ["store"]
        radius = 3000.0
        
    scoring_competitors_raw = []
    city_wide_competitors_raw = []
    if lat and lng:
        scoring_competitors_raw = fetch_nearby_competitors(lat, lng, radius, included_types)
        city_wide_competitors_raw = fetch_nearby_competitors(lat, lng, 15000.0, included_types)
    
    # Filter out the target itself if it appears in competitor list by ID
    def is_valid_competitor(c):
        if c.get("id") == req.place_id:
            return False
        # If user is a small local store, filter out giant chains that miscategorize as grocery_store
        name = c.get("displayName", {}).get("text", "").lower()
        if cat_lower in ["grocery/general retail", "domestic mart", "grocery store"]:
            banned_keywords = ["mega mart", "hypermarket", "supermarket", "smart bazaar", "big bazaar", "reliance smart", "d-mart", "dmart"]
            if any(b in name for b in banned_keywords):
                return False
        return True

    scoring_competitors = [c for c in scoring_competitors_raw if is_valid_competitor(c)]
    
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
    local_competitors_basic = []
    city_competitors_basic = []
    
    for c in scoring_competitors_raw:
        if not is_valid_competitor(c):
            continue
        c_lat = c.get("location", {}).get("latitude")
        c_lng = c.get("location", {}).get("longitude")
        dist = None
        if lat and lng and c_lat and c_lng:
            dist = haversine(lat, lng, c_lat, c_lng)
        
        if dist is not None and dist <= local_radius_km:
            local_competitors_basic.append({
                "name": c.get("displayName", {}).get("text", "Unknown"),
                "rating": c.get("rating", 0),
                "reviews": c.get("userRatingCount", 0),
                "dist": dist
            })
            
    for c in city_wide_competitors_raw:
        if not is_valid_competitor(c):
            continue
        c_lat = c.get("location", {}).get("latitude")
        c_lng = c.get("location", {}).get("longitude")
        dist = None
        if lat and lng and c_lat and c_lng:
            dist = haversine(lat, lng, c_lat, c_lng)
            
        if dist is not None:
            city_competitors_basic.append({
                "name": c.get("displayName", {}).get("text", "Unknown"),
                "rating": c.get("rating", 0),
                "reviews": c.get("userRatingCount", 0),
                "dist": dist
            })
            
    max_local_reviews = max([reviews] + [c["reviews"] for c in local_competitors_basic]) if local_competitors_basic else max(reviews, 1)
    max_city_reviews = max([reviews] + [c["reviews"] for c in city_competitors_basic]) if city_competitors_basic else max(reviews, 1)
    
    def calculate_composite_score(name_text, biz_rating, biz_reviews, dist_km, is_local, max_radius, max_reviews_pool):
        relevance_score = 70.0
        name_lower = name_text.lower()
        if cat_lower in name_lower:
            relevance_score += 30.0
        elif any(word in name_lower for word in cat_lower.split() if len(word) > 3):
            relevance_score += 15.0
        relevance_score = min(100.0, relevance_score)
        
        if dist_km is None:
            distance_score = 0.0
        else:
            distance_score = max(0.0, 100.0 - (dist_km / max_radius) * 100.0)
            
        quality_score = (biz_rating / 5.0) * 50.0
        safe_max = max(1.0, float(max_reviews_pool))
        volume_score = (biz_reviews / safe_max) * 50.0
        prominence_score = quality_score + volume_score
        
        if is_local:
            comp = (relevance_score * 0.25) + (distance_score * 0.40) + (prominence_score * 0.35)
        else:
            comp = (relevance_score * 0.30) + (distance_score * 0.15) + (prominence_score * 0.55)
            
        return round(relevance_score, 1), round(distance_score, 1), round(prominence_score, 1), round(comp, 1)

    target_r_loc, target_d_loc, target_p_loc, target_c_loc = calculate_composite_score(req.name, rating, reviews, 0.0, True, local_radius_km, max_local_reviews)
    target_r_city, target_d_city, target_p_city, target_c_city = calculate_composite_score(req.name, rating, reviews, 0.0, False, 15.0, max_city_reviews)
    
    target_local_dict = {
        "name": req.name, "rating": rating, "reviews": reviews, "distance_km": 0.0,
        "relevance_score": target_r_loc, "distance_score": target_d_loc, "prominence_score": target_p_loc, "composite_score": target_c_loc,
        "is_target": True
    }
    target_city_dict = {
        "name": req.name, "rating": rating, "reviews": reviews, "distance_km": 0.0,
        "relevance_score": target_r_city, "distance_score": target_d_city, "prominence_score": target_p_city, "composite_score": target_c_city,
        "is_target": True
    }
    
    local_pool = [target_local_dict]
    for c in local_competitors_basic:
        r, d, p, comp = calculate_composite_score(c["name"], c["rating"], c["reviews"], c["dist"], True, local_radius_km, max_local_reviews)
        local_pool.append({
            "name": c["name"], "rating": c["rating"], "reviews": c["reviews"], "distance_km": round(c["dist"], 1),
            "relevance_score": r, "distance_score": d, "prominence_score": p, "composite_score": comp,
            "is_target": False
        })
            
    local_pool.sort(key=lambda x: x["composite_score"], reverse=True)
    business_local_rank = 1
    for i, b in enumerate(local_pool):
        if b["is_target"]:
            business_local_rank = i + 1
            break
    local_competitors_list = [{k:v for k,v in c.items() if k != "is_target"} for c in local_pool if not c["is_target"]][:8]
    
    # Generate city-wide competitors list
    city_pool = [target_city_dict]
    for c in city_competitors_basic:
        r, d, p, comp = calculate_composite_score(c["name"], c["rating"], c["reviews"], c["dist"], False, 15.0, max_city_reviews)
        city_pool.append({
            "name": c["name"], "rating": c["rating"], "reviews": c["reviews"], "distance_km": round(c["dist"], 1) if c["dist"] is not None else None,
            "relevance_score": r, "distance_score": d, "prominence_score": p, "composite_score": comp,
            "is_target": False
        })
        
    city_pool.sort(key=lambda x: x["composite_score"], reverse=True)
    business_city_rank = 1
    for i, b in enumerate(city_pool):
        if b["is_target"]:
            business_city_rank = i + 1
            break
    city_competitors_list = [{k:v for k,v in c.items() if k != "is_target"} for c in city_pool if not c["is_target"]][:8]
    
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
        business_local_rank=business_local_rank,
        business_city_rank=business_city_rank,
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
