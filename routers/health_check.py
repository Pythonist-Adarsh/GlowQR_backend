from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import HealthCheckScan
from schemas_health import SearchRequest, PlaceResult, ScanRequest, ScanResponse, CaptureLeadRequest, CompetitorData
from services.serpapi_service import search_places, fetch_place_details, fetch_competitors

router = APIRouter(prefix="/api/health-check", tags=["Health Checker"])

@router.post("/search", response_model=List[PlaceResult])
def search_business(req: SearchRequest):
    results = search_places(req.query, req.lat, req.lng)
    return results

@router.post("/scan", response_model=ScanResponse)
def run_scan(req: ScanRequest, db: Session = Depends(get_db)):
    # 1. Fetch exact business details
    target_data = fetch_place_details(req.place_id)
    if not target_data:
        raise HTTPException(status_code=404, detail="Could not fetch data for this place.")
        
    rating = target_data.get("google_rating", 0)
    reviews = target_data.get("review_count", 0)
    
    # 2. Fetch competitors
    competitors_raw = fetch_competitors(req.category, req.city)
    
    # Filter out the target itself if it appears in competitor list
    competitors = [c for c in competitors_raw if c.get("name").lower() not in req.name.lower()]
    
    comp_reviews = [c.get("reviews", 0) for c in competitors]
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
    # Since SEO and GEO are placeholders right now, we can just use GMB score or a weighted version.
    headline_score = int((gmb_score * 0.5) + (seo_score * 0.25) + (geo_aeo_score * 0.25))
    
    # Issues
    issues = []
    if rating < 4.0:
        issues.append("Your rating is below the 4.0 trust threshold. Customers may choose competitors.")
    if reviews < avg_comp_reviews:
        issues.append(f"You have {reviews} reviews, but the local average is {avg_comp_reviews}. You are losing visibility.")
    elif reviews < top_comp_reviews:
        issues.append(f"Your top competitor has {top_comp_reviews} reviews. They are likely getting the lion's share of local clicks.")
    
    if seo_score == 0:
        issues.append("SEO Score optimization missing. Update your schema and tags. (Coming Soon)")
        
    # 4. Save to DB
    scan_record = HealthCheckScan(
        business_name=req.name,
        google_place_id=req.place_id,
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
    
    comp_list = [CompetitorData(name=c["name"], rating=c["rating"], reviews=c["reviews"]) for c in competitors]
    
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
        issues=issues
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
    return {"status": "success"}
